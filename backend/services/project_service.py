"""Project scanning and Verilog ANSI port-list parsing.

Only ANSI-style headers (`module m(input wire clk, ...);`) are
supported, matching the course material. Modules with `#(parameter...)`
headers or non-ANSI port lists are flagged as unsupported so the UI can
explain the limitation instead of failing cryptically downstream.
"""
import logging
import os
import re

log = logging.getLogger("project")

_IDENT = r"[A-Za-z_]\w*"
_PORT_ITEM_RE = re.compile(
    r"^\s*(?:(input|output|inout)\b)?\s*"
    r"(?:(?:wire|reg|logic)\b\s*)?"
    r"(?:signed\b\s*)?"
    r"(\[[^\]]*\])?\s*"
    r"(" + _IDENT + r")\s*$")


class ProjectError(Exception):
    """User-facing error with a stable code for the API envelope."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _strip_comments(text):
    # Blank out string literals first so "//" inside a string is safe.
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _split_top_commas(text):
    """Split on commas that are not inside () or []."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return parts


def _match_paren(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parse_width(range_text):
    """'[15:0]' -> (15, 0); non-constant expressions -> (raw, raw)."""
    inner = range_text.strip()[1:-1]
    if ":" not in inner:
        return None
    left, right = inner.split(":", 1)
    left, right = left.strip(), right.strip()
    try:
        return int(left, 0), int(right, 0)
    except ValueError:
        return left, right  # keep raw expressions, width unknown


def parse_module_header(name, header):
    """Parse an ANSI port list. Returns (ports, supported, reason).

    ports: [{name, direction, msb, lsb, width}] with width None for
    scalars and for non-constant ranges.
    """
    ports = []
    last_direction = None
    for raw in _split_top_commas(header):
        item = raw.strip()
        if not item:
            continue
        m = _PORT_ITEM_RE.match(item)
        if not m:
            return ports, False, "cannot parse port item: %r" % item
        direction = m.group(1) or last_direction
        if direction is None:
            return ports, False, "non-ANSI port list (missing direction)"
        last_direction = direction
        msb = lsb = width = None
        if m.group(2):
            bounds = _parse_width(m.group(2))
            if bounds is None:
                return ports, False, "cannot parse range: %s" % m.group(2)
            msb, lsb = bounds
            if isinstance(msb, int) and isinstance(lsb, int):
                width = abs(msb - lsb) + 1
        ports.append({"name": m.group(3), "direction": direction,
                      "msb": msb, "lsb": lsb, "width": width})
    return ports, True, None


def parse_verilog_file(path):
    """Parse all module declarations in one .v file."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = _strip_comments(fh.read())
    modules = []
    for m in re.finditer(r"\bmodule\s+(" + _IDENT + r")\s*", text):
        name = m.group(1)
        pos = m.end()
        supported, reason = True, None
        if pos < len(text) and text[pos] == "#":
            # #(parameter ...) headers are not supported by the pipeline.
            modules.append({"name": name, "file": path, "ports": [],
                            "supported": False,
                            "reason": "parameterized module header #(..) not supported"})
            continue
        open_idx = text.find("(", pos)
        semi_idx = text.find(";", pos)
        if open_idx == -1 or (semi_idx != -1 and semi_idx < open_idx):
            modules.append({"name": name, "file": path, "ports": [],
                            "supported": False,
                            "reason": "module without a port list"})
            continue
        close_idx = _match_paren(text, open_idx)
        if close_idx == -1:
            modules.append({"name": name, "file": path, "ports": [],
                            "supported": False,
                            "reason": "unbalanced parentheses in header"})
            continue
        ports, supported, reason = parse_module_header(
            name, text[open_idx + 1:close_idx])
        modules.append({"name": name, "file": path, "ports": ports,
                        "supported": supported, "reason": reason})
    return modules, text


def find_instantiated_names(text, module_names):
    """Names of modules instantiated at least once in the design text."""
    instantiated = set()
    for name in module_names:
        # e.g. "vga_ctrl vga_ctrl_inst (" — module name followed by an
        # instance identifier and an opening paren.
        if re.search(r"\b" + re.escape(name) + r"\s+" + _IDENT + r"\s*\(", text):
            instantiated.add(name)
    return instantiated


def scan_project(path):
    """Scan a project directory: .v files, module table, top candidate."""
    files = sorted(f for f in os.listdir(path)
                   if f.lower().endswith(".v") and
                   os.path.isfile(os.path.join(path, f)))
    if not files:
        raise ProjectError("NO_VERILOG",
                           "目录中没有 .v 文件: %s" % path)
    modules = []
    texts = []
    for fname in files:
        mods, text = parse_verilog_file(os.path.join(path, fname))
        for mod in mods:
            mod["file"] = fname
        modules.extend(mods)
        texts.append(text)
    whole = "\n".join(texts)
    instantiated = find_instantiated_names(whole, [m["name"] for m in modules])
    candidates = [m["name"] for m in modules if m["name"] not in instantiated]
    return {"files": files, "modules": modules, "top_candidates": candidates}


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
