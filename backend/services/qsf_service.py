"""QSF (Quartus Settings File) parse / validate / generate / edit.

Supported subset (real Quartus syntax):
    set_global_assignment -name TOP_LEVEL_ENTITY top
    set_global_assignment -name FAMILY "Cyclone IV E"
    set_global_assignment -name DEVICE EP4CE10F17C8
    set_location_assignment PIN_E1 -to clk
    set_location_assignment PIN_B4 -to vga_data[0]
    create_clock -period 20.000 [get_ports clk]

assign/unassign rewrite the set_location_assignment lines in place and
preserve all other lines (comments included).
"""
import logging
import re

from .project_service import ProjectError

log = logging.getLogger("qsf")

_LOC_RE = re.compile(
    r"^\s*set_location_assignment\s+(PIN_[A-Za-z0-9]+)\s+-to\s+(\S+)\s*$",
    re.I | re.M)
_GLOB_RE = re.compile(
    r"^\s*set_global_assignment\s+-name\s+(\w+)\s+(\"[^\"]*\"|\S+)\s*$",
    re.I | re.M)
_PORT_BIT_RE = re.compile(r"^([A-Za-z_]\w*)(?:\[(\d+)\])?$")


def parse(text):
    """Return {top, globals, assignments:[{pin, port}]} in file order."""
    globals_ = {}
    for m in _GLOB_RE.finditer(text):
        value = m.group(2)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        globals_[m.group(1).upper()] = value
    assignments = []
    for m in _LOC_RE.finditer(text):
        pin = m.group(1).upper().replace("PIN_", "", 1)
        assignments.append({"pin": pin, "port": m.group(2)})
    return {"top": globals_.get("TOP_LEVEL_ENTITY"),
            "globals": globals_,
            "assignments": assignments}


def template(project_name, top):
    """Default QSF for a freshly opened project.

    TOP_LEVEL_ENTITY is intentionally left commented out: the student
    must pick the top module explicitly (Tasks → Top Module), which is
    also what a real Quartus project requires."""
    return (
        "# ------------------------------------------------------------\n"
        "# Quartus Settings File - %s\n"
        "# Simple VGA Simulator (v2) - EP4CE10_Pro virtual board\n"
        "# ------------------------------------------------------------\n"
        'set_global_assignment -name FAMILY "Cyclone IV E"\n'
        "set_global_assignment -name DEVICE EP4CE10F17C8\n"
        "# Select the top module first (Tasks -> Top Module), e.g.:\n"
        "# set_global_assignment -name TOP_LEVEL_ENTITY %s\n"
        "\n"
        "# Pin assignments (edit here or via Pin Planner):\n"
        "#   set_location_assignment PIN_E1  -to clk        # 50MHz clock\n"
        "#   set_location_assignment PIN_M15 -to sys_rst_n  # SW1 RESET, pressed=0\n"
        "#   set_location_assignment PIN_M2  -to key[0]     # SW2 KEY1, pressed=0\n"
        "#   set_location_assignment PIN_L7  -to led[0]     # LED2, 0=on\n"
        "#   set_location_assignment PIN_C2  -to hsync      # VGA_HSYNC\n"
        "#   set_location_assignment PIN_D1  -to vsync      # VGA_VSYNC\n"
        "#   set_location_assignment PIN_B4  -to rgb[0]     # VGA_D0 (RGB565)\n"
        "\n"
        "create_clock -period 20.000 [get_ports clk]\n"
        % (project_name, top or "top"))


def set_top(text, top):
    """Rewrite the TOP_LEVEL_ENTITY line (or append one)."""
    line = "set_global_assignment -name TOP_LEVEL_ENTITY %s" % top
    pat = re.compile(
        r"^\s*set_global_assignment\s+-name\s+TOP_LEVEL_ENTITY\s+\S+.*$",
        re.I | re.M)
    if pat.search(text):
        return pat.sub(line, text, count=1)
    if not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def _normalize_pin(pin):
    m = re.match(r"^\s*(?:PIN_)?([A-Za-z][0-9]+)\s*$", pin or "")
    if not m:
        raise ProjectError("BAD_PIN", "非法引脚名: %r" % pin)
    return m.group(1).upper()


def split_port(port):
    """'rgb[5]' -> ('rgb', 5); 'clk' -> ('clk', None)."""
    m = _PORT_BIT_RE.match((port or "").strip())
    if not m:
        raise ProjectError("BAD_PORT", "非法端口名: %r" % port)
    return m.group(1), (int(m.group(2)) if m.group(2) is not None else None)


def bit_key(port):
    """Normalize a port (with optional bit) to a canonical bit key."""
    name, idx = split_port(port)
    return "%s[%d]" % (name, idx) if idx is not None else name


def expand_port_bits(port, module_ports):
    """Expand a QSF port string to the set of (port_name, bit) it covers.

    A bare bus name covers every bit of the bus.
    """
    name, idx = split_port(port)
    info = next((p for p in module_ports if p["name"] == name), None)
    if info is None:
        raise ProjectError("NO_PORT", "顶层模块没有端口: %s" % name)
    width = info["width"]
    if idx is not None:
        if width is None:
            raise ProjectError("NOT_A_BUS",
                               "端口 %s 是标量，不能位选 [%d]" % (name, idx))
        lo, hi = min(info["msb"], info["lsb"]), max(info["msb"], info["lsb"])
        if not (lo <= idx <= hi):
            raise ProjectError("BIT_RANGE",
                               "位索引 %d 超出端口 %s 的范围 [%s:%s]"
                               % (idx, name, info["msb"], info["lsb"]))
        return {(name, idx)}
    if width is not None and width > 1:
        lo, hi = min(info["msb"], info["lsb"]), max(info["msb"], info["lsb"])
        return {(name, i) for i in range(lo, hi + 1)}
    return {(name, None)}


_LOC_LINE_RE = re.compile(
    r"^(\s*)set_location_assignment\s+(PIN_[A-Za-z0-9]+)\s+-to\s+(\S+)"
    r"\s*(?://[^\n]*)?$", re.I)


def prune_stale(text, module_ports):
    """Drop set_location_assignment lines whose port/bit no longer exists
    in the current top module (e.g. the port was renamed or resized).

    Returns (new_text, dropped) with dropped = [{pin, port}]. Lines that
    do not parse as location assignments are kept untouched.
    """
    kept, dropped = [], []
    for line in text.splitlines(keepends=True):
        m = _LOC_LINE_RE.match(line.rstrip("\r\n"))
        if m:
            try:
                expand_port_bits(m.group(3), module_ports)
            except ProjectError:
                dropped.append({"pin": m.group(2), "port": m.group(3)})
                continue
        kept.append(line)
    return "".join(kept), dropped


def _remove_port_lines(text, port):
    """Drop every set_location_assignment naming exactly `port`."""
    pat = re.compile(
        r"^\s*set_location_assignment\s+PIN_[A-Za-z0-9]+\s+-to\s+"
        + re.escape(port.strip()) + r"\s*(?://[^\n]*)?\r?\n?",
        re.I | re.M)
    return pat.subn("", text)


def assign(text, pin, port, board_pins, module_ports):
    """Insert `set_location_assignment PIN_x -to port`.

    Semantics aligned with the Pin Planner UI:
    - unknown pin -> UNKNOWN_PIN; unknown port -> NO_PORT
    - a bus port must be assigned per bit (name[i]) -> BUS_NEEDS_BIT
    - pin already used by another port -> PIN_CONFLICT
    - re-assigning a port moves it (its old line is dropped first)

    Stale assignments (ports that no longer exist) are pruned up front
    so they never block a new assignment.
    """
    text, _ = prune_stale(text, module_ports)
    pin = _normalize_pin(pin)
    if pin not in board_pins:
        raise ProjectError("UNKNOWN_PIN",
                           "引脚 PIN_%s 不存在于板卡定义" % pin)
    port = port.strip()
    name, idx = split_port(port)
    info = next((p for p in module_ports if p["name"] == name), None)
    if info is None:
        raise ProjectError("NO_PORT", "顶层模块没有端口: %s" % name)
    if idx is None and info["width"] and info["width"] > 1:
        raise ProjectError("BUS_NEEDS_BIT",
                           "总线端口 %s 有 %d 位，请按位分配（如 %s[0]）"
                           % (name, info["width"], name))
    new_bits = expand_port_bits(port, module_ports)
    text, _ = _remove_port_lines(text, port)
    parsed = parse(text)
    for a in parsed["assignments"]:
        if a["pin"] == pin:
            raise ProjectError("PIN_CONFLICT",
                               "PIN_%s 已分配给 %s" % (pin, a["port"]))
        for bit in expand_port_bits(a["port"], module_ports):
            if bit in new_bits:
                label = bit[0] if bit[1] is None else "%s[%d]" % bit
                raise ProjectError("PORT_IN_USE",
                                   "端口 %s 已分配给 PIN_%s"
                                   % (label, a["pin"]))
    new_line = "set_location_assignment PIN_%s -to %s" % (pin, port)
    if not text.endswith("\n"):
        text += "\n"
    return text + new_line + "\n"


def unassign(text, port):
    """Remove all set_location_assignment lines naming `port`."""
    if not port or not port.strip():
        raise ProjectError("BAD_PORT", "非法端口名: %r" % port)
    new_text, n = _remove_port_lines(text, port)
    if n == 0:
        raise ProjectError("NOT_ASSIGNED", "端口 %s 没有分配" % port)
    return new_text
