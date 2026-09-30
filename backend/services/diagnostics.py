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
import tempfile
import threading
import time

import config
from . import toolchain

log = logging.getLogger("diagnostics")

_CACHE_TTL = 5.0
_cache = {"time": 0.0, "result": None}
_cache_lock = threading.Lock()

_VERILATOR_SRC = "module t(input wire a, output wire y); assign y = ~a; endmodule\n"
_YOSYS_SCRIPT = "read_verilog t.v; hierarchy -top t; proc; stat"
_GXX_SRC = '#include <cstdio>\nint main(){std::puts("VGA_BOARD_GXX_OK");return 0;}\n'


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


def _probe(name, version_cmd, version_re, minimum, selfcheck,
           with_selfcheck):
    """Return {path, version, ok, detail} for one tool."""
    provider = toolchain.detect()
    override = toolchain.get_overrides().get(name)
    if provider == "wsl":
        rc, out = _run(["wsl", "bash", "-lc", "command -v %s" % name])
        path = out.strip().splitlines()[0] if rc == 0 and out.strip() else None
    else:
        path = toolchain.resolve(name)
    result = {"path": path, "version": None, "ok": False, "detail": ""}
    if not path:
        result["detail"] = ("not found (native PATH or WSL)"
                            if provider is None else "not found in PATH")
        return result
    argv, cwd = toolchain.wrap_cmd(version_cmd)
    rc, out = _run(argv, cwd=cwd)
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
    if not with_selfcheck:
        result["ok"] = True
        result["detail"] = "version ok" + _suffix(provider, override)
        return result
    ok, detail = selfcheck()
    result["ok"] = ok
    result["detail"] = detail + _suffix(provider, override)
    return result


def _suffix(provider, override):
    if override:
        return " (override)"
    if provider == "wsl":
        return " (via WSL)"
    return ""


def _selfcheck_verilator():
    with tempfile.TemporaryDirectory(prefix="vgachk_vlt_") as tmp:
        src = os.path.join(tmp, "t.v")
        with open(src, "w") as fh:
            fh.write(_VERILATOR_SRC)
        argv, cwd = toolchain.wrap_cmd(
            ["verilator", "--cc", "--top-module", "t", src,
             "--Mdir", os.path.join(tmp, "obj_dir")], cwd=tmp)
        rc, out = _run(argv, cwd=cwd)
        if rc == 0 and os.path.exists(os.path.join(tmp, "obj_dir", "Vt.h")):
            return True, "self-check ok"
        return False, "self-check failed: " + out.strip().splitlines()[-1][:120] if out.strip() else "self-check failed"


def _selfcheck_yosys():
    with tempfile.TemporaryDirectory(prefix="vgachk_ys_") as tmp:
        src = os.path.join(tmp, "t.v")
        with open(src, "w") as fh:
            fh.write(_VERILATOR_SRC)
        argv, cwd = toolchain.wrap_cmd(["yosys", "-p", _YOSYS_SCRIPT], cwd=tmp)
        rc, out = _run(argv, cwd=cwd)
        if rc == 0:
            return True, "self-check ok"
        return False, "self-check failed: " + (out.strip().splitlines()[-1][:120] if out.strip() else "")


def _selfcheck_gxx():
    with tempfile.TemporaryDirectory(prefix="vgachk_cc_") as tmp:
        exe = os.path.join(tmp, "t" + toolchain.exe_suffix())
        argv, cwd = toolchain.wrap_cmd(["g++", "-x", "c++", "-", "-o", exe])
        rc, out = _run(argv, cwd=cwd, input_text=_GXX_SRC)
        if rc != 0 or not os.path.exists(exe):
            return False, "self-check failed (compile): " + (
                out.strip().splitlines()[-1][:120] if out.strip() else "")
        argv, cwd = toolchain.wrap_cmd([exe])
        rc, out = _run(argv, cwd=cwd)
        if rc == 0 and "VGA_BOARD_GXX_OK" in (out or ""):
            return True, "self-check ok (compile+run)"
        return False, "self-check failed (run): rc=%s" % rc


def run_quick(cmd, timeout=15):
    """Public thin wrapper around _run for one-shot external commands."""
    return _run(cmd, timeout=timeout)


def probe_all(force=False, with_selfcheck=True):
    """Probe verilator, g++ and yosys. Returns {tool: {path, version, ok, detail}}.

    with_selfcheck=False is the fast "locate + version" check (the Tools
    dialog's Check button); True additionally compiles/runs a tiny program
    per tool (the Self-Test button)."""
    if force:
        toolchain.detect(force=True)
    with _cache_lock:
        if not force and _cache["result"] and time.time() - _cache["time"] < _CACHE_TTL:
            return _cache["result"]
        result = {
            "verilator": _probe(
                "verilator", ["verilator", "--version"],
                r"Verilator\s+(\d+\.\d+)", config.MIN_VERILATOR,
                _selfcheck_verilator, with_selfcheck),
            "g++": _probe(
                "g++", ["g++", "--version"],
                r"g\+\+.*?(\d+\.\d+(?:\.\d+)?)", config.MIN_GXX,
                _selfcheck_gxx, with_selfcheck),
            "yosys": _probe(
                "yosys", ["yosys", "-V"],
                r"Yosys\s+(\d+\.\d+)", config.MIN_YOSYS,
                _selfcheck_yosys, with_selfcheck),
        }
        _cache["time"] = time.time()
        _cache["result"] = result
        return result
