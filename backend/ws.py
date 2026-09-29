"""Minimal RFC 6455 WebSocket server, stdlib only.

Design notes:
- Each client runs a sender thread. Binary VGA frames use a single-slot
  "latest frame wins" buffer: a slow client drops stale frames instead
  of accumulating backlog (the board is real-time by nature).
- JSON text events are queued with a bound; a client that falls behind
  on events is disconnected rather than growing memory unboundedly.
- Incoming frames are parsed in the caller's (request) thread. Client
  frames must be masked per RFC 6455; ping is answered with pong; a
  close frame ends the connection.
"""
import base64
import hashlib
import logging
import socket
import struct
import threading
from collections import deque

log = logging.getLogger("ws")

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

_MAX_TEXT_QUEUE = 1024


def accept_key(client_key):
    digest = hashlib.sha1((client_key + _GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def build_frame(opcode, payload):
    """Build an unmasked server->client frame."""
    head = bytearray([0x80 | opcode])
    n = len(payload)
    if n < 126:
        head.append(n)
    elif n < 65536:
        head.append(126)
        head += struct.pack(">H", n)
    else:
        head.append(127)
        head += struct.pack(">Q", n)
    return bytes(head) + payload


class WSClient:
    """One connected WebSocket client with a dedicated sender thread."""

    def __init__(self, sock):
        self.sock = sock
        self.alive = True
        self._send_lock = threading.Lock()
        self._cond = threading.Condition()
        self._text_q = deque()
        self._frame = None  # single latest binary frame slot
        self._sender = threading.Thread(target=self._send_loop, daemon=True)
        self._sender.start()

    # ---- outbound API -------------------------------------------------

    def send_json(self, text):
        """Queue a JSON text frame (never dropped silently unless the
        client is hopelessly behind, in which case it is closed)."""
        with self._cond:
            if not self.alive:
                return
            if len(self._text_q) >= _MAX_TEXT_QUEUE:
                log.warning("client fell behind on events; disconnecting")
                self._close_locked()
                return
            self._text_q.append(text.encode("utf-8"))
            self._cond.notify()

    def send_frame(self, data):
        """Offer a binary frame; only the newest one is kept."""
        with self._cond:
            if not self.alive:
                return
            self._frame = data
            self._cond.notify()

    def close(self):
        with self._cond:
            self._close_locked()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def _close_locked(self):
        if self.alive:
            self.alive = False
            self._cond.notify_all()

    # ---- internals ----------------------------------------------------

    def _write(self, data):
        with self._send_lock:
            self.sock.sendall(data)

    def _send_loop(self):
        try:
            while True:
                with self._cond:
                    while self.alive and not self._text_q and self._frame is None:
                        self._cond.wait()
                    if not self.alive:
                        return
                    texts = []
                    while self._text_q:
                        texts.append(self._text_q.popleft())
                    frame = self._frame
                    self._frame = None
                for payload in texts:
                    self._write(build_frame(OP_TEXT, payload))
                if frame is not None:
                    self._write(build_frame(OP_BINARY, frame))
        except OSError:
            self.close()

    def send_pong(self, payload):
        try:
            self._write(build_frame(OP_PONG, payload))
        except OSError:
            self.close()


def _read_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return bytes(buf)


def serve(sock, client, on_message=None):
    """Parse incoming frames on the caller's thread until close.

    Returns when the peer closes, misbehaves, or the connection dies.
    """
    try:
        while client.alive:
            head = _read_exact(sock, 2)
            if head is None:
                break
            fin = head[0] & 0x80
            opcode = head[0] & 0x0F
            masked = head[1] & 0x80
            length = head[1] & 0x7F
            if length == 126:
                ext = _read_exact(sock, 2)
                if ext is None:
                    break
                length = struct.unpack(">H", ext)[0]
            elif length == 127:
                ext = _read_exact(sock, 8)
                if ext is None:
                    break
                length = struct.unpack(">Q", ext)[0]
            if length > 1 << 20:  # this app never sends big upstreams
                break
            mask = b""
            if masked:
                mask = _read_exact(sock, 4)
                if mask is None:
                    break
            payload = _read_exact(sock, length) if length else b""
            if payload is None:
                break
            if masked:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == OP_CLOSE:
                try:
                    client._write(build_frame(OP_CLOSE, payload[:125]))
                except OSError:
                    pass
                break
            if opcode == OP_PING:
                client.send_pong(payload)
                continue
            if opcode == OP_PONG:
                continue
            if not fin:
                break  # fragmentation not needed here; bail out cleanly
            if on_message is not None:
                try:
                    on_message(opcode, payload)
                except Exception:
                    log.exception("ws on_message failed")
    except OSError:
        pass
    finally:
        client.close()
