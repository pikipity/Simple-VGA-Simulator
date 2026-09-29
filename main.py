#!/usr/bin/env python3
"""Simple VGA Simulator v2 launcher.

Starts the local backend (127.0.0.1 only, random port, random token),
opens the EDA tool page in the system browser, and serves until
interrupted or until the watchdog fires after a period of inactivity.

Environment hooks (tests/development only):
    VGA_BOARD_PORT              fixed listen port instead of random
    VGA_BOARD_TOKEN             fixed auth token instead of random
    VGA_BOARD_NO_BROWSER=1      do not open a browser window
    VGA_BOARD_WATCHDOG_TIMEOUT  seconds of inactivity before exit
"""
import logging
import os
import sys
import webbrowser

# Allow running both as `python main.py` and as a frozen executable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from backend.app import create_server


def main():
    os.makedirs(config.data_dir(), exist_ok=True)
    log_path = os.path.join(config.data_dir(), "app.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger("main")

    token = config.make_token()
    server = create_server(token=token, port=config.listen_port())
    port = server.server_address[1]
    url = "http://127.0.0.1:%d/?token=%s" % (port, token)

    log.info("backend v%s listening on 127.0.0.1:%d", config.VERSION, port)
    print("Simple VGA Simulator v%s" % config.VERSION)
    print("EDA tool:  http://127.0.0.1:%d/" % port)
    print("Board:     http://127.0.0.1:%d/board.html" % port)
    print("(URLs opened in your browser carry a one-time session token.)")
    print("Log file:  %s" % log_path)

    if os.environ.get("VGA_BOARD_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception as exc:  # never fail the launch over a browser
            log.warning("webbrowser.open failed: %s", exc)

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        log.info("interrupted by user")
    finally:
        server.shutdown_services()
        server.server_close()
        log.info("backend stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
