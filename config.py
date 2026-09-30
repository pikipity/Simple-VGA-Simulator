"""Global configuration for the Simple VGA Simulator v2 backend.

Security notes:
- The server binds 127.0.0.1 only and requires a per-session token.
- VGA_BOARD_PORT / VGA_BOARD_TOKEN / VGA_BOARD_NO_BROWSER /
  VGA_BOARD_WATCHDOG_TIMEOUT are test/development hooks; production
  launches never set them.
- app.log and settings.json live next to the executable (frozen) or at
  the repo root (source runs); build artifacts live inside the student
  project directory (build/ and output_files/).
"""
import json
import os
import secrets
import sys

VERSION = "2.0.0"

# Pinned tool versions (identical to the course reference environment).
# A different version is NOT a hard error: it lights a yellow warning and
# suggests running the functional self-test.
PINNED_VERILATOR = "4.038"
PINNED_GXX = "11.4.0"
PINNED_YOSYS = "0.9"
TOOLS = ("verilator", "g++", "yosys")

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
BOARD_JSON = os.path.join(REPO_ROOT, "board", "ep4ce10_pro.json")
WRAPPER_TEMPLATE = os.path.join(REPO_ROOT, "sim", "DevelopmentBoard.v.tpl")
# VGA_BOARD_SIM_CPP overrides the simulator source (development/testing).
SIM_CPP = os.environ.get("VGA_BOARD_SIM_CPP") or os.path.join(
    REPO_ROOT, "sim", "simulator.cpp")
WEBUI_DIR = os.path.join(REPO_ROOT, "webui")


def data_dir():
    """Directory for app.log.

    Placed next to the executable (PyInstaller bundle) or at the repo
    root (source runs) so users can actually find it when something
    goes wrong. VGA_BOARD_DATA_DIR overrides (tests/CI).
    """
    override = os.environ.get("VGA_BOARD_DATA_DIR")
    if override:
        return override
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return REPO_ROOT


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


def settings_path():
    return os.path.join(data_dir(), "settings.json")


def load_settings():
    try:
        with open(settings_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(data):
    os.makedirs(data_dir(), exist_ok=True)
    tmp = settings_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, settings_path())
