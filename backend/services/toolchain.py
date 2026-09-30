"""Toolchain provider: native tools vs WSL fallback (Windows only).

The backend itself always runs natively on the host OS. The compile /
simulation tools (verilator / g++ / yosys) are resolved as follows:

- Linux / macOS: system PATH only.
- Windows: native PATH first (MSYS2), then WSL as a whole-toolkit
  fallback (never mixed per-tool).

WSL notes (verified empirically):
- Pipes through wsl.exe are binary-safe (LF is NOT translated on pipes).
- Killing the wsl.exe wrapper does NOT reap the Linux child; reap it
  explicitly with ``pkill -f <sof path>`` (see :func:`reap`).
"""
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys

import config

TOOL_KEYS = ("verilator", "g++", "yosys")

_PROVIDER = None  # 'native' | 'wsl' | None (not probed yet)
_WIN_ABS = re.compile(r"^([A-Za-z]):[\\/]")


def _run_probe(argv, timeout=15):
    try:
        proc = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = proc.stdout or b""
        return proc.returncode, out.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""


def get_overrides():
    """User-specified tool paths from settings.json (empty = auto)."""
    tools = config.load_settings().get("tools") or {}
    return {k: v for k, v in tools.items() if k in TOOL_KEYS and v}


def resolve(tool):
    """Explicit override path if set, else native PATH lookup (None if
    absent). Only meaningful for the native provider; WSL tools are
    resolved inside WSL by name."""
    override = get_overrides().get(tool)
    if override:
        return override
    return shutil.which(tool)


def detect(force=False):
    """Return 'native' | 'wsl' | None (no usable toolchain found)."""
    global _PROVIDER
    if _PROVIDER is not None and not force:
        return _PROVIDER
    if sys.platform != "win32":
        _PROVIDER = "native"
        return _PROVIDER
    if get_overrides():
        # explicit user paths mean: drive the native toolchain
        _PROVIDER = "native"
        return _PROVIDER
    if all(shutil.which(t) for t in TOOL_KEYS):
        _PROVIDER = "native"
        return _PROVIDER
    rc, _ = _run_probe(
        ["wsl", "bash", "-lc",
         "command -v verilator && command -v g++ && command -v yosys"])
    _PROVIDER = "wsl" if rc == 0 else None
    return _PROVIDER


def win_to_wsl(path):
    """D:\\GitHub\\x -> /mnt/d/GitHub/x ; non-Windows paths pass through."""
    m = _WIN_ABS.match(path or "")
    if not m:
        return path
    rest = path[m.end():].replace("\\", "/")
    return "/mnt/%s/%s" % (m.group(1).lower(), rest)


def _translate_arg(arg):
    return win_to_wsl(arg) if _WIN_ABS.match(arg or "") else arg


def wrap_cmd(cmd, cwd=None):
    """Return (argv, popen_cwd) running cmd under the active provider."""
    if detect() == "wsl":
        inner = " ".join(shlex.quote(_translate_arg(a)) for a in cmd)
        if cwd:
            inner = "cd %s && %s" % (shlex.quote(win_to_wsl(cwd)), inner)
        return ["wsl", "bash", "-lc", inner], None
    cmd = list(cmd)
    resolved = resolve(cmd[0])
    if resolved:
        cmd[0] = resolved
    return cmd, cwd


def exe_suffix():
    """Executable suffix for the compiled .sof under the active provider."""
    if sys.platform == "win32" and detect() == "native":
        return ".exe"
    return ""


def needs_pthread():
    """The simulator's std::thread needs -pthread on every POSIX toolchain
    (Linux/macOS native, and WSL even when the host is Windows)."""
    return not (sys.platform == "win32" and detect() == "native")


def join(*parts):
    """Join path fragments in the provider's filesystem convention.

    Host-side paths (project dir, build dir) must use os.path.join even
    under the WSL provider; this helper is for tool-side paths that only
    exist inside the provider (e.g. the Verilator include root).
    """
    if detect() == "wsl":
        return posixpath.join(*parts)
    return os.path.join(*parts)


def sof_argv(sof_path):
    """argv to execute a compiled .sof under the active provider."""
    if detect() == "wsl":
        return ["wsl", "-e", win_to_wsl(sof_path)]
    return [sof_path]


def reap(sof_path):
    """Reap a WSL-side simulator left behind after its wsl.exe was killed.

    -x (exact whole-cmdline match) prevents the pkill wrapper shell from
    matching its own command line.
    """
    if detect() == "wsl" and sof_path:
        _run_probe(["wsl", "bash", "-c",
                    "pkill -xf %s" % shlex.quote(win_to_wsl(sof_path))])
