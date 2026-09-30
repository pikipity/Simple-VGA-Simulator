"""CI smoke test for v2 (stdlib only).

Prereq: app already running with test hooks, e.g.
  VGA_BOARD_NO_BROWSER=1 VGA_BOARD_PORT=8899 VGA_BOARD_TOKEN=ci-token \
  VGA_BOARD_WATCHDOG_TIMEOUT=600 ./dist/simple-vga-simulator/simple-vga-simulator &

Usage:
  basic (all platforms): python tests/ci_smoke.py --port 8899 --token ci-token
  full (Linux runner with verilator/g++/yosys installed):
      python tests/ci_smoke.py --port 8899 --token ci-token --full
"""
import argparse
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ws_client import WSClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

passed = 0


def check(name, cond, detail=""):
    global passed
    if not cond:
        print("[FAIL] %s %s" % (name, detail), flush=True)
        raise SystemExit(1)
    passed += 1
    print("[ok] %s %s" % (name, detail), flush=True)


def call(base, token, path, method="GET", body=None, expect=200):
    req = urllib.request.Request(
        base + path, method=method,
        headers={"X-Board-Token": token, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            code, data = r.code, r.read()
    except urllib.error.HTTPError as e:
        code, data = e.code, e.read()
    if code != expect:
        raise AssertionError("%s %s -> %d (expect %d): %s"
                             % (method, path, code, expect, data[:300]))
    return json.loads(data)


def read_frames(ws, want=10, timeout=15):
    frames = []
    t0 = time.time()
    while len(frames) < want and time.time() - t0 < timeout:
        try:
            opcode, payload = ws.recv(timeout=5)
        except (socket.timeout, TimeoutError):
            continue
        if opcode == 0x2 and len(payload) > 12:
            magic, fno, leds = struct.unpack("<IIB", payload[:9])
            if magic == 0x31474156:
                frames.append((fno, leds))
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--full", action="store_true",
                    help="real compile+program flow (needs verilator/g++/yosys)")
    args = ap.parse_args()
    base = "http://127.0.0.1:%d" % args.port
    tok = args.token

    # ---- basic: server up, auth, static pages, API surface ----
    try:
        urllib.request.urlopen(base + "/api/health", timeout=10)
        raise SystemExit("[FAIL] /api/health without token must be rejected")
    except urllib.error.HTTPError as e:
        check("auth required without token", e.code == 401)

    h = call(base, tok, "/api/health")["data"]
    check("health", h["version"].startswith("2.") and "board" in h, str(h["board"]))

    d = call(base, tok, "/api/diagnostics")["data"]
    check("diagnostics has 3 tools",
          set(d.keys()) == {"verilator", "g++", "yosys"}, str(d))

    b = call(base, tok, "/api/board")["data"]
    check("board json", b["device"] == "EP4CE10F17C8N", b["device"])

    req = urllib.request.Request(base + "/", headers={"X-Board-Token": tok})
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace")
    check("EDA page served", "<" in html and len(html) > 500)
    req = urllib.request.Request(base + "/board.html",
                                 headers={"X-Board-Token": tok})
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "replace")
    check("board page served", "html" in html.lower())

    if not args.full:
        print("CI smoke (basic): %d checks passed" % passed)
        return

    # ---- full: real compile + program + frames (Linux runner) ----
    for tool, info in call(base, tok, "/api/diagnostics")["data"].items():
        check("tool %s available" % tool, info["ok"], info.get("detail", ""))

    tmp = tempfile.mkdtemp(prefix="vga_ci_")
    proj = os.path.join(tmp, "Example_2_BallMove")
    shutil.copytree(os.path.join(REPO_ROOT, "Example", "Example_2_BallMove"),
                    proj)

    r = call(base, tok, "/api/project/open", "POST", {"path": proj})["data"]
    check("open example project", r["top"] == "Simple_VGA", r["top"])

    call(base, tok, "/api/compile/all", "POST", {})
    t0 = time.time()
    while time.time() - t0 < 300:
        st = call(base, tok, "/api/compile/status")["data"]["steps"]
        if not any(s["state"] == "running" for s in st.values()):
            break
        time.sleep(3)
    check("compile all ok",
          all(s["state"] == "ok" for s in st.values()),
          str({k: v["state"] for k, v in st.items()}))
    sof = call(base, tok, "/api/compile/status")["data"]["sof"]
    check("sof produced", sof is not None and sof["name"] == "Simple_VGA.sof",
          str(sof))

    # program guard: board is OFF by default
    r = call(base, tok, "/api/program", "POST", {})
    check("program while OFF rejected", not r["ok"]
          and r["error"]["code"] == "BOARD_OFF", str(r.get("error")))
    # no file selected -> rejected
    r = call(base, tok, "/api/program", "POST", {})
    check("program without sof rejected", not r["ok"]
          and r["error"]["code"] in ("NO_SOF", "BOARD_OFF"), str(r.get("error")))

    sof_path = os.path.join(proj, "output_files", sof["name"])
    call(base, tok, "/api/power", "POST", {"on": True})
    r = call(base, tok, "/api/program", "POST", {"sof": sof_path})
    check("program ok", r["ok"] and r["data"]["conf_done"], str(r["data"]))

    ws = WSClient(args.port, tok)
    frames = read_frames(ws, 20)
    check("frames flowing", len(frames) >= 15, "%d frames" % len(frames))
    check("frame_no increasing",
          all(frames[i + 1][0] > frames[i][0] for i in range(len(frames) - 1)))

    # button SW2 (up) -> led2 -> board led bit1 (see Example_2 QSF/RTL)
    call(base, tok, "/api/input", "POST", {"button": 1, "state": 0})
    time.sleep(1.0)
    frames = read_frames(ws, 8)
    check("SW2 held lights led bit1", bool(frames[-1][1] & 0x02),
          "led_bits=0x%02x" % frames[-1][1])
    call(base, tok, "/api/input", "POST", {"button": 1, "state": 1})
    time.sleep(1.0)
    frames = read_frames(ws, 8)
    check("SW2 released", not (frames[-1][1] & 0x02),
          "led_bits=0x%02x" % frames[-1][1])
    ws.close()

    # re-program without closing anything
    call(base, tok, "/api/compile/all", "POST", {})
    t0 = time.time()
    while time.time() - t0 < 300:
        st = call(base, tok, "/api/compile/status")["data"]["steps"]
        if not any(s["state"] == "running" for s in st.values()):
            break
        time.sleep(3)
    sof2 = call(base, tok, "/api/compile/status")["data"]["sof"]
    check("sof overwritten", sof2["name"] == sof["name"]
          and sof2["mtime"] > sof["mtime"],
          "%s -> %s" % (sof["name"], sof2["name"]))
    r = call(base, tok, "/api/program", "POST", {"sof": sof_path})
    check("reprogram ok", r["ok"])
    ws = WSClient(args.port, tok)
    frames = read_frames(ws, 15)
    check("frames after reprogram", len(frames) >= 10, "%d frames" % len(frames))
    ws.close()

    # power cycle loses configuration (SRAM semantics)
    call(base, tok, "/api/power", "POST", {"on": False})
    time.sleep(0.5)
    bd = call(base, tok, "/api/health")["data"]["board"]
    check("power off clears config", not bd["configured"] and not bd["conf_done"])
    call(base, tok, "/api/power", "POST", {"on": True})
    bd = call(base, tok, "/api/health")["data"]["board"]
    check("after power cycle unconfigured", bd["power"] and not bd["configured"])

    shutil.rmtree(tmp, ignore_errors=True)
    print("CI smoke (full): %d checks passed" % passed)


if __name__ == "__main__":
    main()
