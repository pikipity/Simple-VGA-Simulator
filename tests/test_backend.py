#!/usr/bin/env python3
"""End-to-end backend tests for the Simple VGA Simulator v2.

Run inside WSL (yosys / verilator / g++ required):

    cd /mnt/d/GitHub/Simple-VGA-Simulator
    python3 tests/test_backend.py

The server is started in-process on a random port with a fixed token.
The Assembler stage is exercised for real against tests/stub_sim.cpp
(a genuine Verilator harness), so the produced .sof actually runs and
feeds frames to the WebSocket test. tests/stub_sim.py additionally
covers the "interpreted .sof" spawn path.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

# Test hooks must be set before importing config/backend modules.
os.environ["VGA_BOARD_TOKEN"] = "test-token-123"
os.environ["VGA_BOARD_NO_BROWSER"] = "1"
os.environ["VGA_BOARD_WATCHDOG_TIMEOUT"] = "3600"
os.environ["VGA_BOARD_SIM_CPP"] = os.path.join(TESTS_DIR, "stub_sim.cpp")

sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, TESTS_DIR)

import config  # noqa: E402
from backend.app import create_server  # noqa: E402
from ws_client import WSClient  # noqa: E402

TOKEN = "test-token-123"
VGA_PINS = ["B4", "A2", "B5", "A6", "B6", "F6", "F7", "A7",
            "B7", "E8", "F8", "A8", "B8", "E7", "E6", "A5"]

SERVER = None
PORT = None
PROJ = None  # temp copy of tests/fixtures/proj1


def api(method, path, body=None, token=TOKEN, timeout=180):
    url = "http://127.0.0.1:%d%s" % (PORT, path)
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Board-Token"] = token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read().decode("utf-8"))


def assign(pin, port):
    r = api("POST", "/api/qsf/assign", {"pin": pin, "port": port})
    assert r["ok"], "assign %s -> %s failed: %s" % (pin, port, r)
    return r


def wait_step(step, timeout=180):
    """Compile steps run in the background; poll status until terminal."""
    time.sleep(0.6)  # let the worker flip the step to 'running'
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = api("GET", "/api/compile/status")["data"]["steps"][step]
        if rec["state"] in ("ok", "fail"):
            return rec
        time.sleep(0.4)
    raise AssertionError("step %s did not finish in %ds" % (step, timeout))


class TestBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global SERVER, PORT, PROJ
        PROJ = tempfile.mkdtemp(prefix="vgatest_proj_")
        src = os.path.join(TESTS_DIR, "fixtures", "proj1")
        for f in os.listdir(src):
            if f.endswith(".v"):
                shutil.copy(os.path.join(src, f), PROJ)
        SERVER = create_server(token=TOKEN, port=0)
        PORT = SERVER.server_address[1]
        threading.Thread(target=SERVER.serve_forever,
                         kwargs={"poll_interval": 0.2}, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        if SERVER:
            SERVER.shutdown_services()
            SERVER.shutdown()
            SERVER.server_close()
        if PROJ:
            shutil.rmtree(PROJ, ignore_errors=True)

    # 1. diagnostics ------------------------------------------------------

    def test_01_diagnostics(self):
        r = api("GET", "/api/diagnostics?force=1")
        self.assertTrue(r["ok"], r)
        for tool in ("verilator", "g++", "yosys"):
            info = r["data"][tool]
            print("  [diag] %-9s path=%s version=%s ok=%s detail=%s"
                  % (tool, info["path"], info["version"], info["ok"],
                     info["detail"]))
            self.assertTrue(info["ok"], "%s probe failed: %s" % (tool, info))

    # 2. auth & host guard --------------------------------------------------

    def test_02_auth(self):
        r = api("GET", "/api/health", token=None)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "UNAUTHORIZED")
        r = api("GET", "/api/health", token="wrong-token")
        self.assertFalse(r["ok"])
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/health" % PORT,
            headers={"X-Board-Token": TOKEN, "Host": "evil.example.com"})
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("expected 403 for bad Host")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 403)

    # 3. fs browsing + project open -----------------------------------------

    def test_03_project_open(self):
        r = api("GET", "/api/fs/list?path=" + urllib.parse.quote(PROJ))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["data"]["v_files"], 2)
        self.assertIsInstance(r["data"]["dirs"], list)
        r = api("POST", "/api/project/open", {"path": PROJ})
        self.assertTrue(r["ok"], r)
        data = r["data"]
        print("  [proj] name=%s top=%s files=%s"
              % (data["name"], data["top"], data["files"]))
        self.assertEqual(data["top"], "top")
        self.assertEqual(data["device"], "EP4CE10F17C8")
        self.assertEqual(data["family"], "Cyclone IV E")
        ports = {p["name"]: p for p in data["ports"]}
        self.assertEqual(ports["rgb"]["width"], 16)
        self.assertEqual(ports["rgb"]["dir"], "output")
        self.assertEqual(ports["clk"]["width"], 1)
        self.assertEqual(ports["key"]["dir"], "input")
        self.assertTrue(os.path.isfile(data["qsf_path"]))
        r = api("GET", "/api/project")
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"]["top"], "top")

    # 4. QSF editing ---------------------------------------------------------

    def test_04_qsf_assign(self):
        assign("E1", "clk")
        assign("M15", "rst_n")
        assign("M2", "key[0]")
        assign("M1", "key[1]")
        assign("L7", "led[0]")
        assign("M6", "led[1]")
        assign("C2", "hsync")
        assign("D1", "vsync")
        for i, pin in enumerate(VGA_PINS):
            assign(pin, "rgb[%d]" % i)
        r = api("GET", "/api/qsf")
        self.assertTrue(r["ok"])
        # assignments come back as a port -> pin map
        amap = r["data"]["assignments"]
        self.assertEqual(len(amap), 24)
        self.assertEqual(amap["clk"], "E1")
        self.assertEqual(amap["rgb[15]"], "A5")
        # pin already occupied by another port
        r = api("POST", "/api/qsf/assign", {"pin": "E1", "port": "rst_n"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "PIN_CONFLICT")
        # unknown pin
        r = api("POST", "/api/qsf/assign", {"pin": "Z99", "port": "clk"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "UNKNOWN_PIN")
        # bus port must be assigned per bit
        r = api("POST", "/api/qsf/assign", {"pin": "P3", "port": "led"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "BUS_NEEDS_BIT")
        # re-assigning a port moves it to the new pin
        r = api("POST", "/api/qsf/assign", {"pin": "P3", "port": "led[0]"})
        self.assertTrue(r["ok"], r)
        amap = api("GET", "/api/qsf")["data"]["assignments"]
        self.assertEqual(amap["led[0]"], "P3")
        self.assertNotIn("L7", amap.values())
        assign("L7", "led[0]")  # move back
        # unassign works by port name
        r = api("POST", "/api/qsf/unassign", {"port": "led[1]"})
        self.assertTrue(r["ok"], r)
        amap = api("GET", "/api/qsf")["data"]["assignments"]
        self.assertNotIn("led[1]", amap)
        assign("M6", "led[1]")

    # 5. compile pipeline -----------------------------------------------------

    def test_05_synthesis(self):
        r = api("POST", "/api/compile/synthesis")
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["data"]["started"])  # async contract
        rec = wait_step("synthesis")
        self.assertEqual(rec["state"], "ok")
        self.assertIn("Flow Summary", rec["summary"])
        self.assertIn("Cyclone IV E", rec["summary"])
        self.assertIn("Total registers          : 8", rec["summary"])
        for line in rec["summary"].splitlines():
            if "Total" in line:
                print("  [synthesis]", line.strip())

    def test_06_fitter(self):
        r = api("POST", "/api/compile/fitter")
        self.assertTrue(r["ok"], r)
        rec = wait_step("fitter")
        self.assertEqual(rec["state"], "ok")
        self.assertIn("TimeQuest", rec["summary"])
        self.assertIn("Slack", rec["summary"])
        self.assertNotIn("error", rec["summary"].lower())
        for line in rec["summary"].splitlines():
            if "Slack" in line or "Fmax" in line:
                print("  [fitter]", line.strip())

    def test_07_stale_detection(self):
        with open(os.path.join(PROJ, "top.v"), "a") as fh:
            fh.write("\n// touched by test\n")
        st = api("GET", "/api/compile/status")["data"]["steps"]
        self.assertEqual(st["synthesis"]["state"], "stale")
        self.assertEqual(st["fitter"]["state"], "stale")
        # re-run so downstream tests have fresh state
        self.assertTrue(api("POST", "/api/compile/synthesis")["ok"])
        self.assertEqual(wait_step("synthesis")["state"], "ok")
        self.assertTrue(api("POST", "/api/compile/fitter")["ok"])
        self.assertEqual(wait_step("fitter")["state"], "ok")

    def test_07b_fitter_rejects_handwritten_bad_pin(self):
        # students can hand-edit the .qsf; the Fitter must catch bad pins
        good = api("GET", "/api/qsf")["data"]["text"]
        bad = good + "set_location_assignment PIN_Z99 -to clk\n"
        r = api("POST", "/api/qsf", {"text": bad})
        self.assertTrue(r["ok"], r)
        self.assertTrue(api("POST", "/api/compile/fitter")["ok"])
        rec = wait_step("fitter")
        self.assertEqual(rec["state"], "fail")
        print("  [fitter] bad pin correctly rejected")
        r = api("POST", "/api/qsf", {"text": good})
        self.assertTrue(r["ok"], r)
        self.assertTrue(api("POST", "/api/compile/fitter")["ok"])
        self.assertEqual(wait_step("fitter")["state"], "ok")

    def test_07c_compile_all_increments_revision(self):
        r = api("POST", "/api/compile/all")
        self.assertTrue(r["ok"], r)
        rec = wait_step("assemble", timeout=300)
        self.assertEqual(rec["state"], "ok")
        sof = api("GET", "/api/compile/status")["data"]["sof"]
        self.assertIsNotNone(sof)
        self.assertEqual(sof["revision"], 1)
        self.assertGreater(sof["size_bytes"], 0)
        print("  [compile/all] sof=%s rev=%s size=%d"
              % (sof["name"], sof["revision"], sof["size_bytes"]))

    def test_08_assemble(self):
        r = api("POST", "/api/compile/assemble")
        self.assertTrue(r["ok"], r)
        rec = wait_step("assemble", timeout=300)
        self.assertEqual(rec["state"], "ok")
        sof = api("GET", "/api/compile/status")["data"]["sof"]
        self.assertEqual(sof["revision"], 2)  # revision increments
        sof_path = os.path.join(PROJ, "output_files", sof["name"])
        self.assertTrue(os.path.isfile(sof_path))
        self.assertTrue(os.path.isfile(sof_path + ".json"))
        self.assertEqual(sof["size_bytes"], os.path.getsize(sof_path))
        wrapper = os.path.join(PROJ, "build", "DevelopmentBoard.v")
        with open(wrapper, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("top u_top", text)
        self.assertIn(".clk(clk)", text)
        self.assertIn(".rgb({vga_d[15]", text)
        print("  [assemble] sof=%s rev=%s" % (sof["name"], sof["revision"]))

    # 6. board state machine / programmer ------------------------------------

    def test_09_program_requires_power(self):
        r = api("POST", "/api/program", {})
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], "BOARD_OFF")
        print("  [program] BOARD_OFF correctly rejected: %s"
              % r["error"]["message"])

    def test_10_power_and_program(self):
        r = api("POST", "/api/power", {"on": True})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["data"]["power"])
        self.assertFalse(r["data"]["conf_done"])
        r = api("POST", "/api/program", {})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["data"]["conf_done"], r)
        self.assertTrue(r["data"]["sim_running"])
        self.assertGreaterEqual(r["data"]["rev"], 1)
        print("  [program] conf_done=%s rev=%s"
              % (r["data"]["conf_done"], r["data"]["rev"]))
        # reprogram while powered: old sim is killed, new one runs
        r = api("POST", "/api/program", {})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["data"]["conf_done"])
        # runtime controls
        r = api("POST", "/api/input", {"button": 1, "state": 0})
        self.assertTrue(r["ok"], r)
        r = api("POST", "/api/input", {"button": 1, "state": 1})
        self.assertTrue(r["ok"], r)
        r = api("POST", "/api/ideal", {"on": True})
        self.assertTrue(r["ok"])
        self.assertTrue(r["data"]["ideal"])

    def test_11_program_python_stub(self):
        # interpreted .sof path (stub_sim.py) also works end-to-end
        stub = os.path.join(TESTS_DIR, "stub_sim.py")
        r = api("POST", "/api/program", {"sof": stub})
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["data"]["conf_done"])

    # 7. websocket ------------------------------------------------------------

    def test_12_ws_frames_and_state(self):
        client = WSClient(PORT, TOKEN)
        try:
            # first message must be the board state snapshot
            msg = client.recv_json()
            self.assertEqual(msg["type"], "board")
            self.assertTrue(msg["power"])
            self.assertTrue(msg["conf_done"])
            print("  [ws] initial board state: %s" % msg)
            # the connect snapshot also carries current step states
            got_steps = set()
            deadline = time.time() + 5
            while len(got_steps) < 3 and time.time() < deadline:
                opcode, payload = client.recv(timeout=5)
                if opcode == 0x1:
                    m = json.loads(payload.decode())
                    if m.get("type") == "step":
                        got_steps.add(m["step"])
            self.assertEqual(got_steps, {"synthesis", "fitter", "assemble"})
            print("  [ws] step snapshot ok: %s" % sorted(got_steps))
            # binary VGA frames flow (sim still running from test_11)
            deadline = time.time() + 15
            got = None
            while time.time() < deadline and got is None:
                opcode, payload = client.recv(timeout=10)
                if opcode == 0x2:
                    got = payload
            self.assertIsNotNone(got, "no binary frame received")
            self.assertEqual(len(got), 12 + 640 * 480 * 2)
            # wire bytes are struct.pack('<I', 0x31474156) == b'VAG1'
            # (the AGENTS.md numeric constant is authoritative)
            self.assertEqual(got[:4], b"VAG1")
            print("  [ws] binary frame ok: %d bytes, frame_no=%d leds=0x%02x"
                  % (len(got), int.from_bytes(got[4:8], "little"), got[8]))
            # power off pushes a board state update
            r = api("POST", "/api/power", {"on": False})
            self.assertTrue(r["ok"])
            deadline = time.time() + 10
            seen_off = False
            while time.time() < deadline and not seen_off:
                opcode, payload = client.recv(timeout=5)
                if opcode == 0x1:
                    msg = json.loads(payload.decode())
                    if msg.get("type") == "board" and not msg["power"]:
                        seen_off = True
            self.assertTrue(seen_off, "no power-off board message")
            st = api("GET", "/api/health")["data"]["board"]
            self.assertFalse(st["configured"])
            self.assertFalse(st["conf_done"])
        finally:
            client.close()

    # 8. watchdog ---------------------------------------------------------------

    def test_13_watchdog(self):
        env = dict(os.environ)
        env["VGA_BOARD_WATCHDOG_TIMEOUT"] = "2"
        env["VGA_BOARD_NO_BROWSER"] = "1"
        env["VGA_BOARD_PORT"] = "0"
        env["VGA_BOARD_TOKEN"] = "wd-test"
        proc = subprocess.Popen(
            [sys.executable, os.path.join(REPO_ROOT, "main.py")],
            cwd=REPO_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True)
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            self.fail("watchdog did not stop the server in time:\n" + out)
        print("  [watchdog] server exited rc=%s after idle timeout"
              % proc.returncode)
        self.assertEqual(proc.returncode, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
