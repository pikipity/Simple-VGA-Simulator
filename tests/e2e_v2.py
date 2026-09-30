"""v2 end-to-end integration test: real backend + real toolchain + real sim.

Prereq: backend already running with env hooks, e.g.
  VGA_BOARD_NO_BROWSER=1 VGA_BOARD_PORT=18080 VGA_BOARD_TOKEN=testtok \
  VGA_BOARD_WATCHDOG_TIMEOUT=900 python3 main.py

Run (WSL or Windows, server reachable at 127.0.0.1:18080):
  python3 tests/e2e_v2.py
"""
import json
import struct
import sys
import time
import urllib.request

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from ws_client import WSClient

PORT, TOKEN = 18080, "testtok"
BASE = "http://127.0.0.1:%d" % PORT
ROOT = "/mnt/d/GitHub/Simple-VGA-Simulator"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print("[%s] %s %s" % ("ok" if ok else "FAIL", name, detail), flush=True)


def api(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"X-Board-Token": TOKEN,
                                          "Content-Type": "application/json"},
                                 method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def wait_compile(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = api("/api/compile/status")["data"]["steps"]
        if all(s["state"] in ("ok", "fail") for s in st.values()):
            return st
        time.sleep(2)
    raise TimeoutError("compile timeout")


def read_frames(ws, want=10, timeout=15):
    """Return list of (frame_no, led_bits, payload)."""
    import socket as _socket
    frames = []
    t0 = time.time()
    while len(frames) < want and time.time() - t0 < timeout:
        try:
            opcode, payload = ws.recv(timeout=5)
        except (_socket.timeout, TimeoutError):
            continue
        if opcode == 0x2 and len(payload) > 12:
            magic, fno, leds, flags, _ = struct.unpack("<IIBBH", payload[:12])
            if magic == 0x31474156:
                frames.append((fno, leds, payload[12:]))
    return frames


def wait_steps_idle(ws, timeout=180):
    """Drain WS text messages until no step is running."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st = api("/api/compile/status")["data"]["steps"]
            if not any(s["state"] == "running" for s in st.values()):
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("steps never idle")


# ---------- Example 1: ColorBar ----------
print("=== Example_1_ColorBar ===", flush=True)
r = api("/api/project/open", {"path": ROOT + "/Example/Example_1_ColorBar"})
check("open project", r["ok"] and r["data"]["top"] == "ColorBar")

r = api("/api/compile/all", {})
check("compile started", r["ok"])
st = wait_compile()
check("synthesis ok", st["synthesis"]["state"] == "ok")
check("fitter ok", st["fitter"]["state"] == "ok",
      "Fmax in report: " + ("77" if "77" in st["fitter"]["summary"] else "?"))
check("assemble ok", st["assemble"]["state"] == "ok")
sof = api("/api/compile/status")["data"]["sof"]
check("sof exists", sof is not None and sof["name"] == "ColorBar.sof",
      str(sof))
mtime1 = sof["mtime"] if sof else 0

# program while powered off -> must fail
r = api("/api/program", {})
check("program while OFF rejected", not r["ok"]
      and r["error"]["code"] == "BOARD_OFF", str(r.get("error")))

# power on, then program
r = api("/api/power", {"on": True})
check("power on", r["ok"])
ws = WSClient(PORT, TOKEN)
time.sleep(0.5)
r = api("/api/program", {})
check("program accepted", r["ok"])
time.sleep(4)  # program ceremony
frames = read_frames(ws, 30)
check("frames flowing after program", len(frames) >= 25,
      "%d frames" % len(frames))
if len(frames) >= 2:
    dt_fps = (frames[-1][0] - frames[0][0])
    check("frame rate plausible", dt_fps >= 20, "delta=%d over read window" % dt_fps)
    colors = set()
    for _, _, payload in frames[-3:]:
        for i in range(0, 2000, 2):
            colors.add(struct.unpack_from("<H", payload, i)[0])
    check("color bar has multiple colors", len(colors) > 5, "%d colors" % len(colors))

# ---------- re-program without closing anything ----------
r = api("/api/compile/all", {})
check("recompile started", r["ok"])
wait_compile()
sof2 = api("/api/compile/status")["data"]["sof"]
check("sof overwritten (same name, newer)", sof2
      and sof2["name"] == "ColorBar.sof" and sof2["mtime"] > mtime1,
      str(sof2))
r = api("/api/program", {})
check("reprogram accepted", r["ok"])
time.sleep(4)
frames2 = read_frames(ws, 20)
check("frames after reprogram (no restart)", len(frames2) >= 15,
      "%d frames" % len(frames2))
ws.close()

# power cycle -> config lost
api("/api/power", {"on": False})
time.sleep(1)
r = api("/api/health")["data"]["board"]
check("power off clears config", not r["configured"] and not r["conf_done"],
      str(r))
api("/api/power", {"on": True})
time.sleep(0.5)
r = api("/api/health")["data"]["board"]
check("after power cycle still unconfigured", not r["configured"], str(r))

# ---------- Example 2: BallMove (buttons + LEDs) ----------
print("=== Example_2_BallMove ===", flush=True)
r = api("/api/project/open", {"path": ROOT + "/Example/Example_2_BallMove"})
check("open project", r["ok"] and r["data"]["top"] == "Simple_VGA")
api("/api/compile/all", {})
st = wait_compile()
check("compile all ok", all(s["state"] == "ok" for s in st.values()),
      str({k: v["state"] for k, v in st.items()}))
api("/api/power", {"on": True})
r = api("/api/program", {})
check("program accepted", r["ok"])
time.sleep(4)
ws = WSClient(PORT, TOKEN)
time.sleep(0.5)

api("/api/input", {"button": 1, "state": 0})  # hold SW2 (KEY1 = up)
time.sleep(1)
frames = read_frames(ws, 10)
lit = frames[-1][1] if frames else 0
# Simple_VGA: assign led2 = up -> board led[1] (PIN_M6, silkscreen LED3)
check("SW2 held -> led bit1 lit", bool(lit & 0x02), "led_bits=0x%02x" % lit)

api("/api/input", {"button": 1, "state": 1})  # release
time.sleep(1)
frames = read_frames(ws, 10)
lit = frames[-1][1] if frames else 0
check("SW2 released -> led bit1 dark", not (lit & 0x02), "led_bits=0x%02x" % lit)

# SW1 = RESET is an ordinary button: assign led1 = sys_rst_n
api("/api/input", {"button": 0, "state": 0})  # hold SW1 (RESET)
time.sleep(1)
frames = read_frames(ws, 10)
lit = frames[-1][1] if frames else 0
check("SW1 held -> led bit0 lit (reset asserted)", bool(lit & 0x01),
      "led_bits=0x%02x" % lit)
api("/api/input", {"button": 0, "state": 1})
ws.close()

print()
n_fail = sum(1 for _, ok in results if not ok)
print("E2E: %d/%d passed" % (len(results) - n_fail, len(results)))
sys.exit(1 if n_fail else 0)
