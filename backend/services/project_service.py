"""Project scanning and directory browsing.

Module/port discovery is done by the Yosys Verilog frontend itself
(`read_verilog` + `write_json` on stdout): the same parser that later
runs Analysis & Synthesis decides what the code says, so the IDE can
never disagree with the compiler. Parameterized module headers
(`#(parameter W = 8)`), non-ANSI port lists, cross-file macros and
`include` files all work; parameter-dependent port widths are resolved
with their default values.

Files that fail to read (syntax errors, testbench-style code such as
`$finish` in an initial block, ...) are excluded one at a time — the
offending file is identified from yosys's "file:line: ERROR" output —
so one bad file never hides the modules in the others. Excluded files
are reported under "warnings" in the scan result.
"""
import json
import logging
import os
import re
import subprocess

from . import toolchain

log = logging.getLogger("project")

_YOSYS_TIMEOUT = 60
# "sub.v:12: ERROR: syntax error ..." — yosys echoes the filename exactly
# as passed on the command line (we pass bare relative names).
_ERR_RE = re.compile(r"(?m)^(.+?\.v):(\d+): ERROR: .*$")


class ProjectError(Exception):
    """User-facing error with a stable code for the API envelope."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _quote(fname):
    if '"' in fname or "\n" in fname:
        raise ProjectError("BAD_FILENAME", "文件名含非法字符: %r" % fname)
    return '"%s"' % fname


def yosys_file_args(files):
    """Quoted file arguments for a yosys script (shared by scan/synth)."""
    return " ".join(_quote(f) for f in files)


def _tail(text, n=12):
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines[-n:]) if lines else "(yosys 无输出)"


def _error_line(out, fname):
    for m in _ERR_RE.finditer(out):
        if m.group(1) == fname:
            return m.group(0)
    return _tail(out)


def _yosys_read(proj_path, files):
    """Single-shot yosys read of `files`. Returns (data, bad_file, output).

    data is the parsed JSON dict on success (None on failure); bad_file
    is the filename blamed by yosys's error output (None when it could
    not be identified); output is combined stderr+stdout for reporting.
    """
    script = "read_verilog -I . %s; write_json" % " ".join(
        _quote(f) for f in files)
    argv, cwd = toolchain.wrap_cmd(["yosys", "-q", "-p", script],
                                   cwd=proj_path)
    try:
        proc = subprocess.run(
            argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=_YOSYS_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise ProjectError(
            "TOOL_MISSING",
            "无法运行 yosys: %s（请在 Tools 中检查工具链）" % exc)
    except subprocess.TimeoutExpired:
        raise ProjectError("PARSE_TIMEOUT", "yosys 解析工程超时")
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    combined = (err + "\n" + out).strip()
    if proc.returncode == 0:
        # write_json emits on stdout; tolerate any preamble before '{'.
        # ($finish in a stray testbench aborts the yosys script with
        # rc==0 but no JSON — that case falls through to error blame.)
        brace = out.find("{")
        if brace >= 0:
            try:
                data = json.loads(out[brace:])
            except ValueError:
                data = None
            if isinstance(data, dict) and "modules" in data:
                return data, None, combined
    m = _ERR_RE.search(combined)
    bad = m.group(1) if m else None
    return None, bad, combined


def _modules_from_json(data):
    """yosys JSON -> module table with our stable port dict shape."""
    modules = []
    for name in sorted(data.get("modules", {})):
        if name.startswith("$"):
            continue  # derived parameterizations only appear post-hierarchy
        m = data["modules"][name]
        src = (m.get("attributes") or {}).get("src", "")
        fname = src.split(":", 1)[0] if src else ""
        ports = []
        for pname, p in (m.get("ports") or {}).items():
            n = len(p.get("bits") or [])
            offset = p.get("offset") or 0
            upto = bool(p.get("upto") or 0)
            direction = p.get("direction") or "input"
            if n <= 1 and not offset and not upto:
                msb = lsb = width = None  # scalar port
            elif upto:  # e.g. [0:7]: index 0 is the most significant
                msb, lsb, width = offset, offset + n - 1, n
            else:       # e.g. [7:0] / [16:9]
                msb, lsb, width = offset + n - 1, offset, n
            ports.append({"name": pname, "direction": direction,
                          "msb": msb, "lsb": lsb, "width": width})
        modules.append({"name": name, "file": fname, "ports": ports,
                        "supported": True, "reason": None})
    return modules


def scan_project(path):
    """Scan a project directory: .v files, module table, top candidates."""
    files = sorted(f for f in os.listdir(path)
                   if f.lower().endswith(".v") and
                   os.path.isfile(os.path.join(path, f)))
    if not files:
        raise ProjectError("NO_VERILOG",
                           "目录中没有 .v 文件: %s" % path)
    if toolchain.detect() is None:
        raise ProjectError(
            "TOOL_MISSING",
            "未找到 yosys 工具链（解析工程需要 yosys；请在 Tools 中检查）")
    remaining = list(files)
    warnings = []
    while True:
        data, bad, out = _yosys_read(path, remaining)
        if data is not None:
            break
        if not bad or bad not in remaining:
            raise ProjectError("PARSE_FAIL",
                               "Verilog 解析失败：\n" + _tail(out))
        remaining.remove(bad)
        line = _error_line(out, bad)
        log.warning("scan: excluding %s: %s", bad, line)
        warnings.append({"file": bad, "error": line})
        if not remaining:
            raise ProjectError(
                "PARSE_FAIL", "所有 .v 文件均解析失败：\n" +
                "\n".join(w["error"] for w in warnings))
    modules = _modules_from_json(data)
    instantiated = set()
    for m in data.get("modules", {}).values():
        for cell in (m.get("cells") or {}).values():
            ctype = cell.get("type") or ""
            if ctype and not ctype.startswith("$"):
                instantiated.add(ctype)
    candidates = [m["name"] for m in modules if m["name"] not in instantiated]
    return {"files": files, "modules": modules,
            "top_candidates": candidates, "warnings": warnings}


def browse_folder():
    """Open the OS-native folder picker; return the chosen path or None.

    tkinter is stdlib but not guaranteed everywhere (Ubuntu needs the
    python3-tk package); any failure returns None and the frontend keeps
    using the list browser.
    """
    return _native_browse(folder=True)


def browse_file(patterns=()):
    """OS-native file picker (e.g. choosing a .sof built elsewhere)."""
    return _native_browse(folder=False, patterns=patterns)


def _native_browse(folder, patterns=()):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        if folder:
            path = filedialog.askdirectory()
        else:
            filetypes = [("Programming files", " ".join(patterns))] \
                if patterns else []
            path = filedialog.askopenfilename(filetypes=filetypes)
        return path or None
    except Exception:
        return None
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def list_dir(path):
    """Directory browser payload: subdirs (each with .v count and qsf
    flag) + ALL files in the current dir (students see their .v/.qsf
    alongside everything else, like a real file manager)."""
    if not os.path.isdir(path):
        raise ProjectError("NOT_A_DIR", "不是目录: %s" % path)
    dirs, files, v_count, qsf = [], [], 0, []
    try:
        entries = sorted(os.listdir(path))
    except OSError as exc:
        raise ProjectError("READ_FAIL", str(exc))
    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(path, entry)
        if os.path.isdir(full):
            try:
                sub = os.listdir(full)
                sub_v = sum(1 for f in sub if f.lower().endswith(".v"))
                sub_qsf = any(f.lower().endswith(".qsf") for f in sub)
            except OSError:
                sub_v, sub_qsf = 0, False
            dirs.append({"name": entry, "path": os.path.abspath(full),
                         "v": sub_v, "qsf": sub_qsf})
        elif os.path.isfile(full):
            if entry.lower().endswith(".v"):
                v_count += 1
            elif entry.lower().endswith(".qsf"):
                qsf.append(entry)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            files.append({"name": entry, "size": size})
    parent = os.path.dirname(os.path.normpath(path))
    if parent == os.path.normpath(path):
        parent = None
    return {"path": os.path.abspath(path), "parent": parent,
            "dirs": dirs, "files": files,
            "v_files": v_count, "qsf_files": qsf}
