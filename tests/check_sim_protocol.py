#!/usr/bin/env python3
# check_sim_protocol.py - validate the headless simulator binary protocol.
#
# Run inside WSL from the repo root:
#   wsl bash -lc "cd /mnt/d/GitHub/Simple-VGA-Simulator && python3 tests/check_sim_protocol.py"
#
# Checks:
#   1. SIM_READY handshake on stderr
#   2. frame magic + continuous frame_no, ~60fps over 10s (+-10%)
#   3. color-bar payload spot check (sampling path works)
#   4. 'B' 1 0/1 (SW2 press/release) toggles led_bits bit0
#   5. 'I' 1 sets flags bit0; subsequent press settles immediately
#   6. 'Q' -> clean exit 0

import os
import struct
import subprocess
import sys
import threading
import time

MAGIC = 0x31474156
WIDTH, HEIGHT = 640, 480
PAYLOAD = WIDTH * HEIGHT * 2
HEADER = 12
FPS_MIN, FPS_MAX = 54.0, 66.0

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM_BIN = os.path.join(REPO_ROOT, "tests", "fixtures", "miniboard", "miniboard_sim")


def read_exact(stream, n):
    buf = b""
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            raise EOFError("simulator closed stdout (%d/%d bytes read)" % (len(buf), n))
        buf += chunk
    return buf


class FrameReader:
    def __init__(self, stream):
        self.stream = stream
        self.expected_no = None
        self.frames_read = 0

    def read_frame(self):
        hdr = read_exact(self.stream, HEADER)
        magic, frame_no, led_bits, flags, _reserved = struct.unpack("<IIBBH", hdr)
        assert magic == MAGIC, "bad magic 0x%08X after %d frames" % (magic, self.frames_read)
        if self.expected_no is not None:
            assert frame_no == self.expected_no, \
                "frame_no jump: expected %d, got %d" % (self.expected_no, frame_no)
        self.expected_no = frame_no + 1
        self.frames_read += 1
        payload = read_exact(self.stream, PAYLOAD)
        return frame_no, led_bits, flags, payload


def drain_stderr(proc, sink, ready_event):
    # sole reader of stderr; signals readiness when the handshake line appears
    while True:
        line = proc.stderr.readline()
        if not line:
            return
        text = line.decode(errors="replace").rstrip()
        sink.append(text)
        if "SIM_READY" in text:
            ready_event.set()


def main():
    assert os.path.exists(SIM_BIN), "simulator binary not found: %s" % SIM_BIN
    proc = subprocess.Popen([SIM_BIN], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stderr_lines = []
    ready_event = threading.Event()
    t = threading.Thread(target=drain_stderr,
                         args=(proc, stderr_lines, ready_event), daemon=True)
    t.start()

    try:
        assert ready_event.wait(timeout=15.0), "timeout waiting for SIM_READY"
        print("[ok] handshake: SIM_READY", flush=True)
        fr = FrameReader(proc.stdout)

        # ---- check 1+2: magic/continuity + frame rate over 10s ----
        t0 = time.monotonic()
        count = 0
        while time.monotonic() - t0 < 10.0:
            fr.read_frame()
            count += 1
        elapsed = time.monotonic() - t0
        fps = count / elapsed
        print("[ok] stream: %d frames in %.2fs -> %.2f fps (expect 54..66)"
              % (count, elapsed, fps), flush=True)
        assert FPS_MIN <= fps <= FPS_MAX, "frame rate %.2f fps out of range" % fps

        # ---- check 3: color-bar payload spot check ----
        _, led_bits, flags, payload = fr.read_frame()
        px = lambda x, y: struct.unpack_from("<H", payload, (y * WIDTH + x) * 2)[0]
        assert px(10, 100) == 0xFFFF, "bar0 (white) mismatch: 0x%04X" % px(10, 100)
        assert px(140, 100) == 0xFFE0, "bar1 (yellow) mismatch: 0x%04X" % px(140, 100)
        assert px(500, 400) == 0x07E0, "bar3 (green) mismatch: 0x%04X" % px(500, 400)
        assert led_bits == 0x00, "expected all LEDs dark initially, got 0x%X" % led_bits
        assert flags & 1 == 0, "expected ideal flag clear initially, got 0x%X" % flags
        print("[ok] payload: color bars correct, led_bits=0x00 flags=0x00", flush=True)

        # ---- check 4: SW2 press/release -> led_bits bit0 ----
        proc.stdin.write(b"B" + bytes([1, 0]))  # press SW2 -> key[0]=0 -> led[0] lit
        proc.stdin.flush()
        for _ in range(15):  # let bounce settle (max ~12ms + pickup latency)
            fr.read_frame()
        for _ in range(5):
            _, led_bits, _, _ = fr.read_frame()
            assert led_bits & 1, "led_bits bit0 not set after SW2 press: 0x%X" % led_bits
        print("[ok] SW2 press -> led_bits bit0 = 1 (5 consecutive frames)", flush=True)

        proc.stdin.write(b"B" + bytes([1, 1]))  # release SW2
        proc.stdin.flush()
        for _ in range(15):
            fr.read_frame()
        for _ in range(5):
            _, led_bits, _, _ = fr.read_frame()
            assert not (led_bits & 1), "led_bits bit0 still set after SW2 release: 0x%X" % led_bits
        print("[ok] SW2 release -> led_bits bit0 = 0 (5 consecutive frames)", flush=True)

        # ---- check 5: ideal input flag + immediate settle ----
        proc.stdin.write(b"I" + bytes([1]))
        proc.stdin.flush()
        _, _, flags, _ = fr.read_frame()
        assert flags & 1, "flags bit0 not set after 'I' 1: 0x%X" % flags
        print("[ok] 'I' 1 -> flags bit0 = 1", flush=True)

        proc.stdin.write(b"B" + bytes([2, 0]))  # press SW3 with ideal on
        proc.stdin.flush()
        _, led_bits, _, _ = fr.read_frame()
        assert led_bits & 2, "ideal press not reflected in next frame: 0x%X" % led_bits
        print("[ok] ideal press -> led_bits bit1 = 1 in next frame", flush=True)

        # ---- check 6: 'Q' -> clean exit ----
        proc.stdin.write(b"Q")
        proc.stdin.flush()
        rc = proc.wait(timeout=5)
        assert rc == 0, "expected exit code 0, got %d" % rc
        print("[ok] 'Q' -> process exited cleanly (rc=0)", flush=True)

        print("\nALL CHECKS PASSED", flush=True)
        return 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


if __name__ == "__main__":
    sys.exit(main())
