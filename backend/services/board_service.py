"""Virtual board state machine and simulator process hosting.

States: OFF -> (power on) -> ON/unconfigured -> (program) -> CONFIGURED.
Power-off kills the simulator and clears the configuration (SRAM
semantics). Re-programming while powered kills the old simulator first;
no page or window ever needs to close.

Wire protocol with the simulator process (see AGENTS.md):
    stderr: "SIM_READY" handshake, then free-form log lines
    stdout: binary frames [u32 magic='VGA1'][u32 frame_no][u8 leds]
            [u8 flags][u16 reserved][640*480*2 RGB565 payload]
    stdin:  'B' id state | 'I' 0|1 | 'Q'
"""
import logging
import os
import re
import struct
import subprocess
import sys
import threading
import time

from .project_service import ProjectError
from . import toolchain

log = logging.getLogger("board")

FRAME_MAGIC = 0x31474156  # 'VGA1' little-endian
FRAME_HEADER = 12
FRAME_PAYLOAD = 640 * 480 * 2
READY_TIMEOUT = 10.0


class BoardService:
    def __init__(self, broadcast_state, broadcast_frame, emit_log):
        """broadcast_state(dict), broadcast_frame(bytes),
        emit_log(step, level, text)."""
        self._broadcast_state = broadcast_state
        self._broadcast_frame = broadcast_frame
        self._emit_log = emit_log
        self._lock = threading.RLock()
        self.power = False
        self.configured = False
        self.conf_done = False
        self.ideal = False
        self._sof = None
        self._proc = None
        self._ready = threading.Event()
        self._program_lock = threading.Lock()

    # ---- state --------------------------------------------------------

    def state(self):
        with self._lock:
            return {
                "power": self.power,
                "configured": self.configured,
                "conf_done": self.conf_done,
                "sim_running": self._proc is not None and self._proc.poll() is None,
                "ideal": self.ideal,
            }

    def _push_state(self):
        self._broadcast_state({"type": "board", **self.state()})

    # ---- power ---------------------------------------------------------

    def set_power(self, on):
        on = bool(on)
        with self._lock:
            if on == self.power:
                return self.state()
        if on:
            with self._lock:
                self.power = True
            log.info("board powered on")
        else:
            log.info("board powered off")
            self._kill_sim()
            with self._lock:
                self.power = False
                self.configured = False
                self.conf_done = False
                self._sof = None
        self._push_state()
        return self.state()

    # ---- rebuild unload -------------------------------------------------

    def unload_if_running(self, sof_path):
        """Called when a rebuilt .sof is about to replace the file. If the
        board is running that image, unload it (CONF_DONE off); the board
        must be re-programmed afterwards. Returns True if unloaded."""
        with self._lock:
            running_this = (self._proc is not None
                            and self._sof == sof_path)
        if not running_this:
            return False
        self._emit_log("board", "warn",
                       "设计已重新编译，开发板上的旧配置已卸载——请重新运行 Programmer")
        log.info("design rebuilt; unloading running configuration")
        self._kill_sim()
        with self._lock:
            self.configured = False
            self.conf_done = False
            self._sof = None
        self._push_state()
        return True

    # ---- simulator process --------------------------------------------

    def _spawn(self, sof_path):
        if sof_path.endswith(".py"):
            cmd = [sys.executable, sof_path]
        else:
            cmd = toolchain.sof_argv(sof_path)
        log.info("spawning simulator: %s", cmd[0])
        return subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def _kill_sim(self):
        proc = self._proc
        sof = self._sof
        self._proc = None
        if not proc:
            return
        if proc.poll() is None:
            try:
                proc.stdin.write(b"Q")
                proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    pass
                # killing the wsl.exe wrapper leaves the Linux-side
                # simulator orphaned; reap it explicitly
                toolchain.reap(sof)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                stream.close()
            except OSError:
                pass

    def _stderr_reader(self, proc):
        """Log relay + SIM_READY handshake detection."""
        try:
            for raw in iter(proc.stderr.readline, b""):
                line = raw.decode("utf-8", "replace").rstrip()
                if not line:
                    continue
                if "SIM_READY" in line:
                    self._ready.set()
                    continue
                low = line.lower()
                if "error" in low:
                    level = "error"
                elif "warn" in low:
                    level = "warn"
                else:
                    continue  # swallow info chatter
                self._emit_log("board", level, "[sim] " + line)
        except (OSError, ValueError):
            pass

    @staticmethod
    def _read_exact(stream, n):
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = stream.read(n - len(buf))
            except (OSError, ValueError):
                return None
            if not chunk:
                return None
            buf += chunk
        return bytes(buf)

    def _stdout_reader(self, proc):
        """Parse VGA frames with sliding-window magic resync."""
        stream = proc.stdout
        while True:
            header = self._read_exact(stream, FRAME_HEADER)
            if header is None:
                break
            while len(header) == FRAME_HEADER and \
                    struct.unpack("<I", header[:4])[0] != FRAME_MAGIC:
                nxt = self._read_exact(stream, 1)
                if nxt is None:
                    header = None
                    break
                header = header[1:] + nxt
            if header is None:
                break
            payload = self._read_exact(stream, FRAME_PAYLOAD)
            if payload is None:
                break
            self._broadcast_frame(header + payload)
        log.info("simulator stdout closed")
        # If the simulator died while configured, reflect it on the board.
        with self._lock:
            if self._proc is proc and self.power:
                self.configured = False
                self.conf_done = False
                self._proc = None
        if self.power:
            self._push_state()

    # ---- programmer ----------------------------------------------------

    def program(self, sof_path, progress):
        """Run the Programmer ritual and start the simulator.

        progress(phase, percent) is called as the ceremony advances.
        Raises ProjectError with BOARD_OFF / NO_SOF / SIM_TIMEOUT.
        """
        if not self._program_lock.acquire(blocking=False):
            raise ProjectError("BUSY", "Programmer 正在运行")
        try:
            return self._program(sof_path, progress)
        finally:
            self._program_lock.release()

    def _program(self, sof_path, progress):
        with self._lock:
            if not self.power:
                raise ProjectError(
                    "BOARD_OFF",
                    "未检测到开发板，请检查电源和 USB-Blaster 连接")
        if not sof_path or not os.path.isfile(sof_path):
            raise ProjectError("NO_SOF", "没有可烧录的 .sof 文件，请先完成 Assembler")
        size = os.path.getsize(sof_path)
        with self._lock:
            self.conf_done = False
        self._push_state()
        progress("connecting", 5)
        time.sleep(0.25)
        progress("connecting", 10)
        time.sleep(0.15)
        progress("erasing", 25)
        time.sleep(0.3)
        # programming 25 -> 90, paced by image size, ~1.5s total
        steps = 8
        for i in range(steps):
            time.sleep(max(0.05, min(0.4, size / (steps * 4e6))))
            progress("programming", 25 + int(65.0 * (i + 1) / steps))
        self._kill_sim()
        self._ready.clear()
        proc = self._spawn(sof_path)
        with self._lock:
            self._proc = proc
        threading.Thread(target=self._stderr_reader, args=(proc,),
                         daemon=True).start()
        threading.Thread(target=self._stdout_reader, args=(proc,),
                         daemon=True).start()
        progress("verifying", 92)
        if not self._ready.wait(READY_TIMEOUT):
            self._kill_sim()
            progress("fail", 0)
            raise ProjectError(
                "SIM_TIMEOUT", "仿真进程未在 %ds 内就绪（SIM_READY 超时）"
                % READY_TIMEOUT)
        if self.ideal:
            self._write_cmd(b"I\x01")
        with self._lock:
            self.configured = True
            self.conf_done = True
            self._sof = sof_path
        progress("done", 100)
        self._push_state()
        return self.state()

    # ---- runtime controls ----------------------------------------------

    def _write_cmd(self, data):
        with self._lock:
            proc = self._proc
        if not proc or proc.poll() is not None:
            return False
        try:
            proc.stdin.write(data)
            proc.stdin.flush()
            return True
        except (OSError, BrokenPipeError):
            return False

    def send_input(self, button, state):
        if not (0 <= button <= 4):
            raise ProjectError("BAD_BUTTON", "button 必须在 0..4")
        if state not in (0, 1):
            raise ProjectError("BAD_STATE", "state 必须是 0 或 1")
        self._write_cmd(bytes([ord("B"), button, state]))

    def set_ideal(self, on):
        on = bool(on)
        with self._lock:
            self.ideal = on
        self._write_cmd(b"I" + bytes([1 if on else 0]))
        self._push_state()
        return self.state()

    def shutdown(self):
        self._kill_sim()
