"""Three-level probing of external tools (verilator / g++ / yosys).

Levels: PATH lookup -> version check against locked minimums -> a
minimal functional self-check compiled in a temp directory. Results are
cached briefly so the UI can poll cheaply.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

import config

log = logging.getLogger("diagnostics")

_CACHE_TTL = 5.0
_cache = {"time": 0.0, "result": None}
_cache_lock = threading.Lock()

_VERILATOR_SRC = "module t(input wire a, output wire y); assign y = ~a; endmodule\n"
_YOSYS_SCRIPT = "read_verilog t.v; hierarchy -top t; proc; stat"
_GXX_SRC = "int main() { return 0; }\n"


def _run(cmd, cwd=None, timeout=60, input_text=None):
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, timeout=timeout, input=input_text,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return proc.returncode, proc.stdout or ""
    except subprocess.TimeoutExpired:
        return -1, "timeout after %ds" % timeout
    except OSError as exc:
        return -1, str(exc)


def _version_tuple(text):
    m = re.search(r"(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _probe(name, version_cmd, version_re, minimum, selfcheck):
    """Return {path, version, ok, detail} for one tool."""
    path = shutil.which(name)
    result = {"path": path, "version": None, "ok": False, "detail": ""}
    if not path:
        result["detail"] = "not found in PATH"
        return result
    rc, out = _run(version_cmd)
    if rc != 0 and not out:
        result["detail"] = "version probe failed"
        return result
    m = re.search(version_re, out)
    version = m.group(1) if m else None
    result["version"] = version
    vtup = _version_tuple(version)
    if vtup is None:
        result["detail"] = "could not parse version from: %s" % out.strip().splitlines()[0][:80]
        return result
    if minimum and vtup < minimum:
        result["detail"] = "version %s < required %s" % (
            version, ".".join(str(x) for x in minimum))
        return result
    ok, detail = selfcheck()
    result["ok"] = ok
    result["detail"] = detail
    return result


def _selfcheck_verilator():
    with tempfile.TemporaryDirectory(prefix="vgachk_vlt_") as tmp:
        src = os.path.join(tmp, "t.v")
        with open(src, "w") as fh:
            fh.write(_VERILATOR_SRC)
        rc, out = _run(
            ["verilator", "--cc", "--top-module", "t", src,
             "--Mdir", os.path.join(tmp, "obj_dir")], cwd=tmp)
        if rc == 0 and os.path.exists(os.path.join(tmp, "obj_dir", "Vt.h")):
            return True, "self-check ok"
        return False, "self-check failed: " + out.strip().splitlines()[-1][:120] if out.strip() else "self-check failed"


def _selfcheck_yosys():
    with tempfile.TemporaryDirectory(prefix="vgachk_ys_") as tmp:
        src = os.path.join(tmp, "t.v")
        with open(src, "w") as fh:
            fh.write(_VERILATOR_SRC)
        rc, out = _run(["yosys", "-p", _YOSYS_SCRIPT], cwd=tmp)
        if rc == 0:
            return True, "self-check ok"
        return False, "self-check failed: " + (out.strip().splitlines()[-1][:120] if out.strip() else "")


def _selfcheck_gxx():
    with tempfile.TemporaryDirectory(prefix="vgachk_cc_") as tmp:
        exe = os.path.join(tmp, "t.exe" if sys.platform == "win32" else "t")
        rc, out = _run(["g++", "-x", "c++", "-", "-o", exe], input_text=_GXX_SRC)
        if rc == 0 and os.path.exists(exe):
            return True, "self-check ok"
        return False, "self-check failed: " + (out.strip().splitlines()[-1][:120] if out.strip() else "")


def probe_all(force=False):
    """Probe verilator, g++ and yosys. Returns {tool: {path, version, ok, detail}}."""
    with _cache_lock:
        if not force and _cache["result"] and time.time() - _cache["time"] < _CACHE_TTL:
            return _cache["result"]
        result = {
            "verilator": _probe(
                "verilator", ["verilator", "--version"],
                r"Verilator\s+(\d+\.\d+)", config.MIN_VERILATOR,
                _selfcheck_verilator),
            "g++": _probe(
                "g++", ["g++", "--version"],
                r"g\+\+.*?(\d+\.\d+(?:\.\d+)?)", config.MIN_GXX,
                _selfcheck_gxx),
            "yosys": _probe(
                "yosys", ["yosys", "-V"],
                r"Yosys\s+(\d+\.\d+)", config.MIN_YOSYS,
                _selfcheck_yosys),
        }
        _cache["time"] = time.time()
        _cache["result"] = result
        return result
