"""Global configuration for the Simple VGA Simulator v2 backend.

Security notes:
- The server binds 127.0.0.1 only and requires a per-session token.
- VGA_BOARD_PORT / VGA_BOARD_TOKEN / VGA_BOARD_NO_BROWSER /
  VGA_BOARD_WATCHDOG_TIMEOUT are test/development hooks; production
  launches never set them.
- DATA_DIR holds only the application log. Build artifacts live inside
  the student project directory (build/ and output_files/).
"""
import os
import secrets
import sys

VERSION = "2.0.0"

# Locked external tool minimum versions (see AGENTS.md platform table).
MIN_VERILATOR = (4, 0)
MIN_YOSYS = (0, 9)
MIN_GXX = (7, 0)
TOOLS = ("verilator", "g++", "yosys")

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
BOARD_JSON = os.path.join(REPO_ROOT, "board", "ep4ce10_pro.json")
WRAPPER_TEMPLATE = os.path.join(REPO_ROOT, "sim", "DevelopmentBoard.v.tpl")
# VGA_BOARD_SIM_CPP overrides the simulator source (development/testing).
SIM_CPP = os.environ.get("VGA_BOARD_SIM_CPP") or os.path.join(
    REPO_ROOT, "sim", "simulator.cpp")
WEBUI_DIR = os.path.join(REPO_ROOT, "webui")


def data_dir():
    """Per-user data directory for app.log (platform conventions)."""
    override = os.environ.get("VGA_BOARD_DATA_DIR")
    if override:
        return override
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        return os.path.join(base, "vga-board")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "vga-board")
    return os.path.join(home, ".local", "share", "vga-board")


def listen_port():
    """0 = system-assigned port (default); env override is for tests."""
    try:
        return int(os.environ.get("VGA_BOARD_PORT", "0"))
    except ValueError:
        return 0


def make_token():
    return os.environ.get("VGA_BOARD_TOKEN") or secrets.token_urlsafe(24)


def watchdog_timeout():
    """Seconds of API inactivity before the backend exits."""
    try:
        return float(os.environ.get("VGA_BOARD_WATCHDOG_TIMEOUT", "120"))
    except ValueError:
        return 120.0
