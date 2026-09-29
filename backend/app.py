"""HTTP layer: routing, static hosting, token auth, Host-header check,
watchdog, WebSocket fan-out.

Security constraints (by design contract):
- binds 127.0.0.1 only (see create_server)
- every /api/* and /ws request requires the per-session token
  (X-Board-Token header; /ws also accepts ?token= for browser clients)
- the Host header must be 127.0.0.1 / localhost (DNS-rebinding guard)
- the token is never written to logs
"""
import json
import logging
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import config
from . import ws as wsmod
from .services import build_service, board_service, diagnostics, \
    project_service, qsf_service
from .services.project_service import ProjectError

log = logging.getLogger("app")

_HOST_RE = re.compile(r"^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", re.I)

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    # explicit text/javascript: Windows registry lookups may claim
    # text/plain, which browsers refuse to load as an ES module
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

_PLACEHOLDER_HTML = """<!doctype html><meta charset="utf-8">
<title>VGA Board Backend</title>
<body style="font-family:monospace;background:#222;color:#ddd;padding:2em">
<h2>Simple VGA Simulator v2 - backend running</h2>
<p>webui/ is not built yet. WebSocket state feed:</p>
<pre id="log"></pre>
<script>
const token = new URLSearchParams(location.search).get('token') || '';
const ws = new WebSocket(`ws://${location.host}/ws?token=${token}`);
const log = m => document.getElementById('log').textContent += m + "\\n";
ws.onmessage = e => (typeof e.data === 'string') ? log(e.data)
  : log('[binary frame ' + e.data.byteLength + ' bytes]');
ws.onopen = () => log('[ws connected]');
</script></body>"""


class Backend:
    """Shared application state: project session, services, WS clients."""

    def __init__(self, token):
        self.token = token
        self.last_activity = time.time()
        self._activity_lock = threading.Lock()
        self._clients = set()
        self._clients_lock = threading.Lock()
        self._project = None
        self._project_lock = threading.Lock()
        self.build = build_service.BuildService(
            get_project=lambda: self._project,
            emit_log=self.emit_log,
            emit_step=self.emit_step)
        self.board = board_service.BoardService(
            broadcast_state=self.broadcast_json,
            broadcast_frame=self.broadcast_frame,
            emit_log=self.emit_log)

    # activity tracking (watchdog)
    def touch(self):
        with self._activity_lock:
            self.last_activity = time.time()

    def idle_seconds(self):
        with self._activity_lock:
            return time.time() - self.last_activity

    # websocket fan-out
    def add_client(self, client):
        with self._clients_lock:
            self._clients.add(client)
        # snapshot: board state, then current pipeline step states
        client.send_json(json.dumps({"type": "board", **self.board.state()}))
        try:
            steps = self.build.status()["steps"]
        except ProjectError:
            steps = {s: {"state": "idle", "summary": ""}
                     for s in build_service.STEPS}
        for step, rec in steps.items():
            client.send_json(json.dumps({
                "type": "step", "step": step, "state": rec["state"],
                "summary": rec.get("summary", "")}, ensure_ascii=False))

    def remove_client(self, client):
        with self._clients_lock:
            self._clients.discard(client)
        client.close()

    def broadcast_json(self, obj):
        text = json.dumps(obj, ensure_ascii=False)
        with self._clients_lock:
            clients = list(self._clients)
        for client in clients:
            client.send_json(text)

    def broadcast_frame(self, data):
        with self._clients_lock:
            clients = list(self._clients)
        for client in clients:
            client.send_frame(data)

    def emit_log(self, step, level, text):
        self.broadcast_json({"type": "log", "step": step,
                             "level": level, "text": text})

    def emit_step(self, step, state, summary):
        self.broadcast_json({"type": "step", "step": step,
                             "state": state, "summary": summary})

    def emit_program(self, phase, percent):
        self.broadcast_json({"type": "program", "phase": phase,
                             "percent": percent})

    # project session
    def open_project(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ProjectError("NOT_A_DIR", "不是目录: %s" % path)
        scan = project_service.scan_project(path)
        name = os.path.basename(os.path.normpath(path))
        qsf_files = [f for f in os.listdir(path) if f.lower().endswith(".qsf")]
        qsf_path = os.path.join(path, name + ".qsf")
        if not os.path.exists(qsf_path):
            if qsf_files:
                qsf_path = os.path.join(path, sorted(qsf_files)[0])
            else:
                top_guess = scan["top_candidates"][0] if scan["top_candidates"] else "top"
                with open(qsf_path, "w", encoding="utf-8") as fh:
                    fh.write(qsf_service.template(name, top_guess))
        with open(qsf_path, "r", encoding="utf-8") as fh:
            qsf = qsf_service.parse(fh.read())
        top = qsf["top"] if qsf["top"] in [m["name"] for m in scan["modules"]] else None
        if top is None and scan["top_candidates"]:
            top = scan["top_candidates"][0]
        with self._project_lock:
            self._project = {
                "name": name, "path": path,
                "qsf_path": qsf_path,
                "qsf_name": os.path.basename(qsf_path),
                "files": scan["files"],
                "modules": scan["modules"],
                "top": top,
            }
        log.info("opened project %s (%d verilog files)", path, len(scan["files"]))
        return self.project_info()

    def project_info(self):
        with self._project_lock:
            proj = dict(self._project) if self._project else None
        if not proj:
            raise ProjectError("NO_PROJECT", "尚未打开工程")
        top_mod = next((m for m in proj["modules"]
                        if m["name"] == proj["top"]), None)
        ports = []
        if top_mod and top_mod["supported"]:
            ports = [{"name": p["name"], "dir": p["direction"],
                      "width": p["width"] or 1} for p in top_mod["ports"]]
        try:
            with open(proj["qsf_path"], encoding="utf-8") as fh:
                globals_ = qsf_service.parse(fh.read())["globals"]
        except OSError:
            globals_ = {}
        out = dict(proj)
        out["ports"] = ports
        out["device"] = globals_.get("DEVICE") or self.build.board.get("device")
        out["family"] = globals_.get("FAMILY") or self.build.board.get("family")
        return out

    def shutdown(self):
        self.board.shutdown()
        with self._clients_lock:
            clients = list(self._clients)
        for client in clients:
            client.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "VGABoard/" + config.VERSION

    # Never log request lines (they may carry ?token=).
    def log_message(self, fmt, *args):
        return

    # ---- plumbing -----------------------------------------------------

    @property
    def backend(self):
        return self.server.backend

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, data=None):
        self._send_json({"ok": True, "data": data})

    def _fail(self, code, message, status=200):
        self._send_json({"ok": False,
                         "error": {"code": code, "message": message}}, status)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(min(length, 4 << 20))
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ProjectError("BAD_JSON", "请求体不是合法 JSON")

    def _check_host(self):
        host = self.headers.get("Host", "")
        return bool(_HOST_RE.match(host))

    def _check_token(self, query):
        if self.headers.get("X-Board-Token") == self.backend.token:
            return True
        tokens = parse_qs(query).get("token", [])
        return bool(tokens) and tokens[0] == self.backend.token

    # ---- dispatch ------------------------------------------------------

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if not self._check_host():
                self._fail("BAD_HOST", "Forbidden", status=403)
                return
            if path == "/ws":
                self._handle_ws(parsed.query)
                return
            if path.startswith("/api/"):
                self.backend.touch()
                if not self._check_token(parsed.query):
                    self._fail("UNAUTHORIZED", "missing or bad token", status=401)
                    return
                self._route_api("GET", path, None, parsed.query)
                return
            if path.startswith("/ws"):
                self._fail("NOT_FOUND", "not found", status=404)
                return
            self._serve_static(path)
        except BrokenPipeError:
            pass
        except ProjectError as exc:
            self._fail(exc.code, exc.message)
        except Exception as exc:
            log.exception("GET %s failed", path)
            self._fail("INTERNAL", "%s: %s" % (type(exc).__name__, exc),
                       status=500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if not self._check_host():
                self._fail("BAD_HOST", "Forbidden", status=403)
                return
            if not path.startswith("/api/"):
                self._fail("NOT_FOUND", "not found", status=404)
                return
            self.backend.touch()
            if not self._check_token(parsed.query):
                self._fail("UNAUTHORIZED", "missing or bad token", status=401)
                return
            body = self._read_body()
            self._route_api("POST", path, body, parsed.query)
        except BrokenPipeError:
            pass
        except ProjectError as exc:
            self._fail(exc.code, exc.message)
        except Exception as exc:
            log.exception("POST %s failed", path)
            self._fail("INTERNAL", "%s: %s" % type(exc).__name__ + ": " + str(exc),
                       status=500)

    # ---- API routes -----------------------------------------------------

    def _route_api(self, method, path, body, query):
        b = self.backend
        route = (method, path)

        if route == ("GET", "/api/health"):
            self._ok({"version": config.VERSION,
                      "board": b.board.state()})
        elif route == ("POST", "/api/heartbeat"):
            self._ok({"idle": round(b.idle_seconds(), 1)})
        elif route == ("GET", "/api/diagnostics"):
            force = parse_qs(query).get("force") == ["1"]
            self._ok(diagnostics.probe_all(force=force))
        elif route == ("GET", "/api/fs/home"):
            self._ok({"path": os.path.expanduser("~")})
        elif route == ("GET", "/api/fs/list"):
            qs = parse_qs(query)
            target = qs.get("path", [os.path.expanduser("~")])[0]
            self._ok(project_service.list_dir(os.path.expanduser(target)))
        elif route == ("POST", "/api/project/open"):
            self._ok(b.open_project(body.get("path", "")))
        elif route == ("GET", "/api/project"):
            self._ok(b.project_info())
        elif route == ("POST", "/api/project/top"):
            self._set_top(body.get("top", ""))
        elif route == ("GET", "/api/qsf"):
            self._get_qsf()
        elif route == ("POST", "/api/qsf"):
            self._save_qsf(body.get("text", ""))
        elif route == ("POST", "/api/qsf/assign"):
            self._qsf_assign(body.get("pin", ""), body.get("port", ""))
        elif route == ("POST", "/api/qsf/unassign"):
            self._qsf_unassign(body.get("port", ""))
        elif route == ("POST", "/api/compile/synthesis"):
            self._compile_async(["synthesis"])
        elif route == ("POST", "/api/compile/fitter"):
            self._compile_async(["fitter"])
        elif route == ("POST", "/api/compile/assemble"):
            self._compile_async(["assemble"])
        elif route == ("POST", "/api/compile/all"):
            self._compile_async(["synthesis", "fitter", "assemble"])
        elif route == ("GET", "/api/compile/status"):
            self._ok(b.build.status())
        elif route == ("POST", "/api/program"):
            self._program(body)
        elif route == ("POST", "/api/power"):
            self._ok(b.board.set_power(bool(body.get("on"))))
        elif route == ("POST", "/api/input"):
            b.board.send_input(int(body.get("button", -1)),
                               int(body.get("state", -1)))
            self._ok(True)
        elif route == ("POST", "/api/ideal"):
            self._ok(b.board.set_ideal(bool(body.get("on"))))
        elif route == ("GET", "/api/board"):
            with open(config.BOARD_JSON, "r", encoding="utf-8") as fh:
                self._ok(json.load(fh))
        else:
            self._fail("NOT_FOUND", "unknown API: %s %s" % (method, path),
                       status=404)

    # ---- API handlers with project context ------------------------------

    def _compile_async(self, steps):
        """Kick off a background build; the reply is immediate and all
        progress flows over the WebSocket."""
        b = self.backend
        b.project_info()  # NO_PROJECT fails synchronously
        if not b.build.start_async(steps):
            self._fail("BUSY", "编译正在进行中，请稍候")
            return
        self._ok({"started": True})

    def _current_qsf_path(self):
        return self.backend.project_info()["qsf_path"]

    def _top_module_ports(self):
        proj = self.backend.project_info()
        scan = project_service.scan_project(proj["path"])
        with open(proj["qsf_path"], encoding="utf-8") as fh:
            qsf = qsf_service.parse(fh.read())
        top = qsf["top"] or proj["top"]
        mod = next((m for m in scan["modules"] if m["name"] == top), None)
        if mod is None:
            raise ProjectError("NO_TOP", "找不到顶层模块 %s" % top)
        if not mod["supported"]:
            raise ProjectError("UNSUPPORTED_MODULE",
                               "顶层模块 %s: %s" % (top, mod["reason"]))
        return mod["ports"]

    def _set_top(self, top):
        proj = self.backend.project_info()
        if not re.match(r"^[A-Za-z_]\w*$", top or ""):
            raise ProjectError("BAD_TOP", "非法模块名: %r" % top)
        path = proj["qsf_path"]
        with open(path, "r", encoding="utf-8") as fh:
            text = qsf_service.set_top(fh.read(), top)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        with self.backend._project_lock:
            self.backend._project["top"] = top
        self._ok(self.backend.project_info())

    def _get_qsf(self):
        path = self._current_qsf_path()
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        parsed = qsf_service.parse(text)
        # frontend Pin Planner consumes a port -> pin map
        assignments = {a["port"]: a["pin"] for a in parsed["assignments"]}
        self._ok({"text": text, "assignments": assignments,
                  "top": parsed["top"]})

    def _save_qsf(self, text):
        path = self._current_qsf_path()
        if not isinstance(text, str) or "set_global_assignment" not in text:
            raise ProjectError("BAD_QSF", "QSF 内容无效")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self._get_qsf()

    def _qsf_assign(self, pin, port):
        path = self._current_qsf_path()
        ports = self._top_module_ports()
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        text = qsf_service.assign(text, pin, port,
                                  self.backend.build.pin2wrapper, ports)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self._get_qsf()

    def _qsf_unassign(self, port):
        path = self._current_qsf_path()
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        text = qsf_service.unassign(text, port)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        self._get_qsf()

    def _program(self, body):
        b = self.backend
        sof = body.get("sof")
        if not sof:
            proj = b.project_info()
            sof_info = b.build.status().get("sof")
            if sof_info:
                sof = os.path.join(proj["path"], "output_files",
                                   sof_info["name"])
        try:
            state = b.board.program(sof, b.emit_program)
        except ProjectError as exc:
            if exc.code not in ("BOARD_OFF", "NO_SOF"):
                b.emit_program("fail", 0)
            raise
        self._ok(state)

    # ---- static & websocket --------------------------------------------

    def _serve_static(self, path):
        if path == "/":
            rel = "index.html"
        else:
            rel = path.lstrip("/")
        base = os.path.abspath(config.WEBUI_DIR)
        full = os.path.abspath(os.path.join(base, rel))
        if full != base and not full.startswith(base + os.sep):
            self._fail("FORBIDDEN", "forbidden", status=403)
            return
        if os.path.isfile(full):
            ext = os.path.splitext(full)[1].lower()
            ctype = _CONTENT_TYPES.get(ext, "application/octet-stream")
            with open(full, "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if rel == "index.html":
            # Placeholder while webui/ is under construction.
            data = _PLACEHOLDER_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._fail("NOT_FOUND", "not found", status=404)

    def _handle_ws(self, query):
        if not self._check_token(query):
            self._fail("UNAUTHORIZED", "missing or bad token", status=401)
            return
        key = self.headers.get("Sec-WebSocket-Key")
        upgrade = self.headers.get("Upgrade", "").lower()
        if not key or upgrade != "websocket":
            self._fail("BAD_WS", "not a websocket upgrade", status=400)
            return
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n\r\n" % wsmod.accept_key(key))
        self.request.sendall(response.encode("ascii"))
        self.close_connection = True
        client = wsmod.WSClient(self.request)
        self.backend.add_client(client)
        log.info("ws client connected (%d total)", len(self.backend._clients))
        try:
            wsmod.serve(self.request, client)
        finally:
            self.backend.remove_client(client)
            log.info("ws client disconnected")


class BackendServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, token):
        super().__init__(addr, Handler)
        self.backend = Backend(token)
        self._watchdog_stop = threading.Event()
        timeout = config.watchdog_timeout()
        self._watchdog_timeout = timeout
        self._watchdog = threading.Thread(
            target=self._watchdog_loop, daemon=True)
        self._watchdog.start()

    def _watchdog_loop(self):
        while not self._watchdog_stop.wait(1.0):
            if self.backend.idle_seconds() > self._watchdog_timeout:
                log.info("watchdog: idle for %.0fs, shutting down",
                         self._watchdog_timeout)
                # shutdown() must run outside the serve_forever thread.
                threading.Thread(target=self.shutdown, daemon=True).start()
                return

    def shutdown_services(self):
        self._watchdog_stop.set()
        self.backend.shutdown()


def create_server(token, port=0):
    """Bind 127.0.0.1 only; port 0 lets the OS pick a free port."""
    return BackendServer(("127.0.0.1", port), token)
