"""Minimal WebSocket client for tests (stdlib only, client-side masking)."""
import base64
import json
import os
import socket
import struct


class WSClient:
    def __init__(self, port, token, host="127.0.0.1", path="/ws", timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        req = (
            "GET %s?token=%s HTTP/1.1\r\n"
            "Host: 127.0.0.1:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n" % (path, token, port, key))
        self.sock.sendall(req.encode("ascii"))
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise IOError("handshake failed: connection closed")
            resp += chunk
        status = resp.split(b"\r\n", 1)[0]
        if b"101" not in status:
            raise IOError("handshake rejected: %s" % status.decode())

    def _read_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise IOError("connection closed")
            buf += chunk
        return buf

    def recv(self, timeout=10):
        """Return (opcode, payload) of the next unmasked server frame."""
        self.sock.settimeout(timeout)
        head = self._read_exact(2)
        opcode = head[0] & 0x0F
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack(">H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._read_exact(8))[0]
        payload = self._read_exact(length) if length else b""
        return opcode, payload

    def recv_json(self, timeout=10):
        opcode, payload = self.recv(timeout)
        assert opcode == 0x1, "expected text frame, got opcode %d" % opcode
        return json.loads(payload.decode("utf-8"))

    def send_text(self, text):
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        head = bytearray([0x81])
        n = len(payload)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", n)
        head += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(head) + masked)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
