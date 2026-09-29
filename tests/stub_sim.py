#!/usr/bin/env python3
"""Stub .sof used by tests: speaks the simulator wire protocol.

Prints SIM_READY on stderr, then streams well-formed VGA frames at
~60 Hz on stdout. Responds to stdin commands: 'B' id state (tracked),
'I' 0|1, 'Q' (exit). The LED nibble in the frame header cycles with the
frame counter so tests can tell frames apart.
"""
import struct
import sys
import threading

MAGIC = 0x31474156
PAYLOAD = bytes(640 * 480 * 2)  # legal-size dummy frame body

_stop = threading.Event()


def _reader():
    stream = sys.stdin.buffer
    while not _stop.is_set():
        c = stream.read(1)
        if not c:
            break
        if c == b"B":
            stream.read(2)
        elif c == b"I":
            stream.read(1)
        elif c == b"Q":
            _stop.set()
            return


def main():
    sys.stderr.write("SIM_READY\n")
    sys.stderr.flush()
    threading.Thread(target=_reader, daemon=True).start()
    frame_no = 0
    import time
    while not _stop.is_set():
        frame_no += 1
        header = struct.pack("<IIBBH", MAGIC, frame_no, frame_no & 0xF, 0, 0)
        try:
            sys.stdout.buffer.write(header + PAYLOAD)
            sys.stdout.buffer.flush()
        except (BrokenPipeError, ValueError):
            break
        time.sleep(1.0 / 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
