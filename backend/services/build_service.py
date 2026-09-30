"""Build pipeline: Synthesis (yosys) / Fitter (pin check + timing
estimate) / Assembler (verilator + g++).

The UI vocabulary mirrors Quartus Prime; the student never sees the
underlying tools. Each step streams its output line by line to the
Messages window via the emit_log callback and records its state (with a
hash of the input files) in <project>/build/.build_state.json so a
source edit marks completed steps as stale.

Timing model (teaching approximation, per AGENTS.md):
    longest path = max over modules of yosys `ltp` after `synth` (gate level)
    est_period_ns = 0.2 * levels + 1.5
    Fmax_MHz      = 1000 / est_period_ns
    slack_ns      = 20 - est_period_ns      (50 MHz clock)
Negative slack is a Critical Warning only (matches real Quartus: timing
failure does not block bitstream generation; the simulator is a
functional model).
"""
import datetime
import glob
import hashlib
import json
import logging
import os
import re
import subprocess
import threading

import config
from . import project_service, qsf_service, toolchain
from .project_service import ProjectError

log = logging.getLogger("build")

STEPS = ("synthesis", "fitter", "assemble")
_LATCH_RE = re.compile(r"latch", re.I)
_CLK_PORT_RE = re.compile(r"clk|clock", re.I)


def load_board():
    with open(config.BOARD_JSON, "r", encoding="utf-8") as fh:
        return json.load(fh)


def pin_wrapper_map(board):
    """FPGA pin -> wrapper signal expression, e.g. 'B4' -> 'vga_d[0]'."""
    m = {}
    res = board["resources"]
    m[res["clk"]["pin"]] = "clk"
    for entry in res.values():
        wrapper = entry.get("wrapper")
        if not wrapper:
            continue
        if entry.get("kind") == "vga_bus":
            for i, pin in enumerate(entry["pins"]):
                m[pin] = "%s[%d]" % (wrapper, i)
        else:
            m[entry["pin"]] = wrapper
    return m


def pin_directions(board):
    """FPGA pin -> direction from the wrapper's point of view."""
    dirs = {}
    res = board["resources"]
    dirs[res["clk"]["pin"]] = "input"
    for entry in res.values():
        kind = entry.get("kind")
        if kind == "button":
            dirs[entry["pin"]] = "input"
        elif kind in ("led", "vga"):
            dirs[entry["pin"]] = "output"
        elif kind == "vga_bus":
            for pin in entry["pins"]:
                dirs[pin] = "output"
    return dirs


def _input_hash(proj_path, files, qsf_text, top):
    h = hashlib.sha1()
    h.update((top or "").encode())
    h.update(qsf_text.encode("utf-8", "replace"))
    for fname in files:
        h.update(fname.encode())
        with open(os.path.join(proj_path, fname), "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


class BuildService:
    def __init__(self, get_project, emit_log, emit_step,
                 before_sof_replace=None):
        """get_project() returns the live project context dict or None;
        emit_log(step, level, text) and emit_step(step, state, summary)
        fan out to WebSocket clients. before_sof_replace(path) is called
        just before a freshly built .sof replaces the old one (the board
        uses it to unload a running configuration)."""
        self._get_project = get_project
        self._emit_log = emit_log
        self._emit_step = emit_step
        self._before_sof_replace = before_sof_replace
        self._lock = threading.Lock()
        self._running = set()           # steps currently executing
        self._running_lock = threading.Lock()
        self.board = load_board()
        self.pin2wrapper = pin_wrapper_map(self.board)
        self.pin_dir = pin_directions(self.board)

    # ---- async execution (compile endpoints return immediately) -------

    def start_async(self, steps):
        """Run pipeline steps on a background thread; False if busy."""
        if not self._lock.acquire(blocking=False):
            return False

        def work():
            impl = {"synthesis": self._synthesis, "fitter": self._fitter,
                    "assemble": self._assemble}
            try:
                for step in steps:
                    impl[step]()
            except ProjectError:
                pass  # step already marked fail and logged
            except Exception:
                log.exception("background build failed")
            finally:
                with self._running_lock:
                    self._running.clear()
                self._lock.release()

        threading.Thread(target=work, daemon=True).start()
        return True

    # ---- state persistence -------------------------------------------

    def _build_dir(self, proj):
        path = os.path.join(proj["path"], "build")
        os.makedirs(path, exist_ok=True)
        return path

    def _output_dir(self, proj):
        path = os.path.join(proj["path"], "output_files")
        os.makedirs(path, exist_ok=True)
        return path

    def _state_path(self, proj):
        return os.path.join(proj["path"], "build", ".build_state.json")

    def _load_state(self, proj):
        try:
            with open(self._state_path(proj), "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {"steps": {}}

    def _save_state(self, proj, state):
        os.makedirs(os.path.dirname(self._state_path(proj)), exist_ok=True)
        tmp = self._state_path(proj) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1)
        os.replace(tmp, self._state_path(proj))

    def status(self):
        """Per-step state with live staleness detection + sof info."""
        proj = self._require_project()
        state = self._load_state(proj)
        try:
            current = self._current_hash(proj)
        except OSError:
            current = None
        with self._running_lock:
            running = set(self._running)
        out = {}
        for step in STEPS:
            rec = dict(state["steps"].get(step) or {"state": "idle"})
            rec.setdefault("time", None)
            rec.setdefault("summary", "")
            if step in running:
                rec["state"] = "running"
            elif rec["state"] == "ok" and current and rec.get("hash") != current:
                rec["state"] = "stale"
            out[step] = rec
        sof = None
        sof_name = state.get("sof")
        if sof_name:
            sof_path = os.path.join(proj["path"], "output_files", sof_name)
            if os.path.isfile(sof_path):
                st = os.stat(sof_path)
                sof = {"name": sof_name, "size_bytes": st.st_size,
                       "mtime": st.st_mtime}
        return {"steps": out, "sof": sof}

    # ---- helpers ------------------------------------------------------

    def _require_project(self):
        proj = self._get_project()
        if not proj:
            raise ProjectError("NO_PROJECT", "请先打开工程")
        return proj

    def _current_hash(self, proj):
        scan = project_service.scan_project(proj["path"])
        qsf_text = self._read_qsf(proj)
        top = self._resolve_top(proj, scan)
        return _input_hash(proj["path"], scan["files"], qsf_text, top)

    def _read_qsf(self, proj):
        with open(proj["qsf_path"], "r", encoding="utf-8") as fh:
            return fh.read()

    def _resolve_top(self, proj, scan):
        qsf = qsf_service.parse(self._read_qsf(proj))
        names = [m["name"] for m in scan["modules"]]
        if qsf["top"] and qsf["top"] in names:
            return qsf["top"]
        if scan["top_candidates"]:
            return scan["top_candidates"][0]
        if names:
            return names[0]
        raise ProjectError("NO_MODULE", "工程中没有找到模块")

    def _set_step(self, proj, step, state, summary, state_hash=None,
                  extra=None):
        store = self._load_state(proj)
        record = {
            "state": state,
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "summary": summary,
        }
        if extra:
            record.update(extra)
        store["steps"][step] = record
        if state_hash:
            store["steps"][step]["hash"] = state_hash
        self._save_state(proj, store)
        with self._running_lock:
            self._running.discard(step)
        self._emit_step(step, state, summary, extra)
        return store

    def _begin_step(self, step):
        with self._running_lock:
            self._running.add(step)
        self._emit_step(step, "running", "")

    def _run_streaming(self, step, cmd, cwd, stream=True):
        """Run a tool, streaming combined output to Messages line by line.

        stream=False 时只收集输出（告警/错误仍转发），用于时序估算等
        不需要把整份工具日志倒进 Messages 的场合。
        """
        argv, popen_cwd = toolchain.wrap_cmd(cmd, cwd)
        self._emit_log(step, "info", "$ " + " ".join(cmd))
        try:
            proc = subprocess.Popen(
                argv, cwd=popen_cwd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            self._emit_log(step, "error", "无法启动 %s: %s" % (cmd[0], exc))
            raise ProjectError("TOOL_MISSING", "找不到工具 %s" % cmd[0])
        lines = []
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            low = line.lower()
            level = "info"
            if "error" in low:
                level = "error"
            elif "warning" in low:
                level = "warn"
            if stream or level != "info":
                self._emit_log(step, level, line)
        proc.wait()
        proc.stdout.close()
        return proc.returncode, lines

    # ---- Synthesis ----------------------------------------------------

    def run_synthesis(self):
        with self._lock:
            try:
                return self._synthesis()
            finally:
                with self._running_lock:
                    self._running.discard("synthesis")

    def _synthesis(self):
        proj = self._require_project()
        scan = project_service.scan_project(proj["path"])
        top = self._resolve_top(proj, scan)
        mod = next((m for m in scan["modules"] if m["name"] == top), None)
        if mod and not mod["supported"]:
            raise ProjectError("UNSUPPORTED_MODULE",
                               "顶层模块 %s: %s" % (top, mod["reason"]))
        cmd = ["yosys", "-p",
               "read_verilog %s; hierarchy -top %s; proc; check; flatten; stat; "
               "dump t:$dff t:$dffe t:$adff t:$sdff t:$dffsr t:$aldff "
               "t:$dlatch t:$adlatch t:$dlatchsr"
               % (" ".join(scan["files"]), top)]
        self._begin_step("synthesis")
        rc, lines = self._run_streaming("synthesis", cmd, proj["path"])
        if rc != 0:
            summary = "Analysis & Synthesis failed"
            self._set_step(proj, "synthesis", "fail", summary)
            raise ProjectError("SYNTHESIS_FAIL", summary + "（详见 Messages）")
        le = self._parse_stat(lines, top)
        regs, latches = self._parse_regs(lines)
        if latches:
            self._emit_log("synthesis", "warn",
                           "推断出 %d 位 latch（组合逻辑不完整赋值），请检查代码"
                           % latches)
        summary = self._flow_summary(top, le, regs, latches)
        state_hash = _input_hash(proj["path"], scan["files"],
                                 self._read_qsf(proj), top)
        self._set_step(proj, "synthesis", "ok", summary, state_hash)
        return {"top": top, "logic_elements": le, "registers": regs,
                "latches": latches, "summary": summary}

    @staticmethod
    def _parse_stat(lines, top):
        """Total cell count (logic elements) from the flattened stat."""
        le = 0
        section_re = re.compile(r"^===\s+(\S+)\s+===$")
        row_re = re.compile(r"^\s+(\S+)\s+(\d+)\s*$")
        in_top = False
        found = False
        for line in lines:
            m = section_re.match(line)
            if m:
                in_top = m.group(1) == top
                continue
            if in_top and "Number of cells:" in line:
                found = True
                continue
            if in_top:
                r = row_re.match(line)
                if r:
                    le += int(r.group(2))
        if not found:
            # Fallback: sum every section (older yosys corner cases).
            for line in lines:
                r = row_re.match(line)
                if r:
                    le += int(r.group(2))
        return le

    @staticmethod
    def _parse_regs(lines):
        """Register/latch bit counts from the `dump` cell blocks."""
        regs = latches = 0
        cell_re = re.compile(r"^\s*cell\s+(\S+)\s+\S+\s*$")
        width_re = re.compile(r"^\s*parameter\s+\\WIDTH\s+(\d+)")
        latch_cell = False
        for line in lines:
            m = cell_re.match(line)
            if m:
                latch_cell = bool(_LATCH_RE.search(m.group(1)))
                continue
            w = width_re.match(line)
            if w:
                n = int(w.group(1))
                if latch_cell:
                    latches += n
                regs += n
        return regs, latches

    @staticmethod
    def _flow_summary(top, le, regs, latches):
        now = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        return "\n".join([
            "Flow Summary",
            "-----------------------------",
            "Flow Status              : Successful - %s" % now,
            "Top-level Entity Name    : %s" % top,
            "Family                   : Cyclone IV E",
            "Device                   : EP4CE10F17C8N",
            "Total logic elements     : %d" % le,
            "Total registers          : %d" % regs,
            "Inferred latches         : %d" % latches,
            "Total pins               : 26 of 180 used (virtual board)",
        ])

    # ---- Fitter --------------------------------------------------------

    def run_fitter(self):
        with self._lock:
            try:
                return self._fitter()
            finally:
                with self._running_lock:
                    self._running.discard("fitter")

    def _validate_pins(self, proj, scan, top):
        """Cross-check QSF assignments against board JSON and top ports.

        Returns (issues, assignments); issues are (level, message) with
        level 'warn' or 'error'."""
        qsf = qsf_service.parse(self._read_qsf(proj))
        mod = next((m for m in scan["modules"] if m["name"] == top), None)
        if mod is None:
            raise ProjectError("NO_TOP", "找不到顶层模块 %s" % top)
        if not mod["supported"]:
            raise ProjectError("UNSUPPORTED_MODULE",
                               "顶层模块 %s: %s" % (top, mod["reason"]))
        ports = {p["name"]: p for p in mod["ports"]}
        issues = []
        valid = []
        seen_bits = {}
        for a in qsf["assignments"]:
            pin, port = a["pin"], a["port"]
            if pin not in self.pin2wrapper:
                issues.append(("error",
                               "PIN_%s 不存在于板卡（非法引脚）" % pin))
                continue
            try:
                bits = qsf_service.expand_port_bits(port, mod["ports"])
            except ProjectError as exc:
                issues.append(("error", exc.message))
                continue
            name, _ = qsf_service.split_port(port)
            pinfo = ports[name]
            want_dir = self.pin_dir.get(pin)
            if want_dir == "input" and pinfo["direction"] == "output":
                issues.append(("error",
                               "方向冲突：PIN_%s 是输入资源（按键/时钟），不能连接输出端口 %s"
                               % (pin, name)))
                continue
            if want_dir == "output" and pinfo["direction"] == "input":
                issues.append(("error",
                               "方向冲突：PIN_%s 是输出资源（LED/VGA），不能连接输入端口 %s"
                               % (pin, name)))
                continue
            dup = False
            for bit in bits:
                if bit in seen_bits:
                    label = bit[0] if bit[1] is None else "%s[%d]" % bit
                    issues.append(("error",
                                   "端口 %s 同时分配到 PIN_%s 和 PIN_%s"
                                   % (label, seen_bits[bit], pin)))
                    dup = True
                seen_bits[bit] = pin
            if not dup:
                valid.append({"pin": pin, "port": port, "bits": bits,
                              "direction": pinfo["direction"]})
        # vga_d bus must be all-or-nothing (16 bits).
        vga_pins = set(self.board["resources"]["vga_d"]["pins"])
        assigned_vga = vga_pins & {a["pin"] for a in valid}
        if assigned_vga and assigned_vga != vga_pins:
            issues.append(("error",
                           "VGA 数据总线必须分配全部 16 位（当前 %d/16）"
                           % len(assigned_vga)))
        # Clock sanity warnings.
        clk_pins = {a["pin"] for a in valid
                    if _CLK_PORT_RE.search(qsf_service.split_port(a["port"])[0])}
        clk_pin = self.board["resources"]["clk"]["pin"]
        for a in valid:
            name = qsf_service.split_port(a["port"])[0]
            if _CLK_PORT_RE.search(name) and a["pin"] != clk_pin:
                issues.append(("warn",
                               "时钟端口 %s 分配在 PIN_%s：not a dedicated clock pin"
                               "（50MHz 晶振在 PIN_%s）" % (name, a["pin"], clk_pin)))
        if clk_pin not in {a["pin"] for a in valid} and any(
                _CLK_PORT_RE.search(p["name"]) for p in mod["ports"]
                if p["direction"] == "input"):
            issues.append(("warn",
                           "未分配 50MHz 时钟引脚 PIN_%s" % clk_pin))
        # Unassigned ports.
        assigned_bits = set(seen_bits)
        for p in mod["ports"]:
            if p["width"] and p["width"] > 1:
                lo = min(p["msb"], p["lsb"])
                hi = max(p["msb"], p["lsb"])
                whole = {(p["name"], i) for i in range(lo, hi + 1)}
                missing = whole - assigned_bits
                if len(missing) == len(whole):
                    issues.append(("warn", self._unassigned_msg(p)))
                elif missing:
                    issues.append((
                        "warn" if p["direction"] == "input" else "error",
                        "总线端口 %s 仅部分分配（缺 %d 位）"
                        % (p["name"], len(missing))))
            elif (p["name"], None) not in assigned_bits:
                issues.append(("warn", self._unassigned_msg(p)))
        return issues, valid

    @staticmethod
    def _unassigned_msg(port):
        if port["direction"] == "input":
            return "输入端口 %s 未分配引脚，将被上拉为 1" % port["name"]
        return "输出端口 %s 未分配引脚，悬空" % port["name"]

    def _estimate_timing(self, proj, scan, top):
        # 门级网表深度估算：synth 映射到通用门后跑 ltp，取所有模块中的最大值
        # （ltp 对每个模块各报一行 "Longest topological path ... (length=N)"）
        cmd = ["yosys", "-p",
               "read_verilog %s; synth -top %s; ltp"
               % (" ".join(scan["files"]), top)]
        rc, lines = self._run_streaming("fitter", cmd, proj["path"],
                                        stream=False)
        depth = None
        if rc == 0:
            depths = [int(m.group(1)) for line in lines
                      for m in [re.search(
                          r"[Ll]ongest topological path.*length=(\d+)", line)]
                      if m]
            if depths:
                depth = max(depths)
        if depth is None:
            self._emit_log("fitter", "warn",
                           "无法测量最长路径，本次时序报告不可用")
            return None
        # Cyclone IV 门级经验估算：~0.2ns/级（多级门会打包进同一 LE）+ 固定开销
        period_ns = 0.2 * depth + 1.5
        fmax_mhz = 1000.0 / period_ns
        slack_ns = 20.0 - period_ns
        return depth, period_ns, fmax_mhz, slack_ns

    @staticmethod
    def _timing_report(depth, period_ns, fmax_mhz, slack_ns):
        if depth is None:
            return "\n".join([
                "+-------------------------------------------------------+",
                "; TimeQuest Timing Analyzer - Slow 1200mV 85C Model     ;",
                "+---------------------------+---------------------------+",
                "; Clock                     ; clk (PIN_E1, 50 MHz)      ;",
                "; Estimated Fmax            ; N/A (estimation failed)   ;",
                "+---------------------------+---------------------------+",
            ])
        return "\n".join([
            "+-------------------------------------------------------+",
            "; TimeQuest Timing Analyzer - Slow 1200mV 85C Model     ;",
            "+---------------------------+---------------------------+",
            "; Clock                     ; clk (PIN_E1, 50 MHz)      ;",
            "; Required Period           ; %20.3f ns ;" % 20.0,
            "; Estimated Period          ; %20.3f ns ;" % period_ns,
            "; Worst-case Slack          ; %20.3f ns ;" % slack_ns,
            "; Estimated Fmax            ; %19.2f MHz ;" % fmax_mhz,
            "; Longest path (levels)     ; %20d    ;" % depth,
            "+---------------------------+---------------------------+",
        ])

    @staticmethod
    def _pin_report(assignments, pin2wrapper):
        rows = ["+-----------+-------------------+---------------+",
                "; Pin       ; Student Port      ; Board Signal  ;",
                "+-----------+-------------------+---------------+"]
        for a in sorted(assignments, key=lambda x: x["pin"]):
            rows.append("; PIN_%-6s ; %-17s ; %-13s ;"
                        % (a["pin"], a["port"], pin2wrapper.get(a["pin"], "?")))
        rows.append("+-----------+-------------------+---------------+")
        return "\n".join(rows)

    def _fitter(self):
        proj = self._require_project()
        scan = project_service.scan_project(proj["path"])
        top = self._resolve_top(proj, scan)
        self._begin_step("fitter")
        issues, valid = self._validate_pins(proj, scan, top)
        for level, msg in issues:
            self._emit_log("fitter", level, msg)
        if any(level == "error" for level, _ in issues):
            summary = "Fitter failed: %d error(s)" % sum(
                1 for lv, _ in issues if lv == "error")
            self._set_step(proj, "fitter", "fail", summary)
            raise ProjectError("FITTER_FAIL", summary + "（详见 Messages）")
        timing = self._estimate_timing(proj, scan, top)
        if timing is None:
            depth = period_ns = fmax_mhz = slack_ns = None
        else:
            depth, period_ns, fmax_mhz, slack_ns = timing
        report = (self._pin_report(valid, self.pin2wrapper) + "\n\n"
                  + self._timing_report(depth, period_ns, fmax_mhz, slack_ns))
        if slack_ns is not None and slack_ns < 0:
            # 与真实 Quartus 一致：时序未收敛是 Critical Warning，不阻断流程
            # （仿真器是功能模型，时序问题不影响虚拟板运行）
            self._emit_log("fitter", "warn",
                           "Critical Warning: Timing requirements not met "
                           "(estimated Fmax %.1f MHz < 50 MHz, slack %.3f ns)"
                           % (fmax_mhz, slack_ns))
            report += ("\n\nCritical Warning: Timing requirements not met "
                       "(estimated, for reference only)")
        pins = [{"pin": a["pin"], "port": a["port"],
                 "resource": self.pin2wrapper.get(a["pin"], ""),
                 "dir": self.pin_dir.get(a["pin"], "")}
                for a in sorted(valid, key=lambda x: x["pin"])]
        timing_info = None
        if fmax_mhz is not None:
            timing_info = {"fmax_mhz": round(fmax_mhz, 2),
                           "required_mhz": 50.0,
                           "slack_ns": round(slack_ns, 3),
                           "pass": slack_ns >= 0, "depth": depth}
        state_hash = _input_hash(proj["path"], scan["files"],
                                 self._read_qsf(proj), top)
        self._set_step(proj, "fitter", "ok", report, state_hash,
                       extra={"pins": pins, "timing": timing_info})
        return {"assignments": len(valid),
                "fmax_mhz": None if fmax_mhz is None else round(fmax_mhz, 2),
                "slack_ns": None if slack_ns is None else round(slack_ns, 3),
                "warnings": len(issues),
                "summary": report}

    # ---- Assembler -----------------------------------------------------

    def run_assemble(self):
        with self._lock:
            try:
                return self._assemble()
            finally:
                with self._running_lock:
                    self._running.discard("assemble")

    def _gen_wrapper(self, mod, assignments):
        """Render DevelopmentBoard.v: student top port <- pin -> wrapper.

        Returns (verilog_text, warnings)."""
        bit_src = {}  # (port_name, bit|None) -> wrapper expression
        for a in assignments:
            wrapper = self.pin2wrapper[a["pin"]]
            for bit in a["bits"]:
                bit_src[bit] = wrapper
        warnings = []
        conns = []
        for p in mod["ports"]:
            name, direction = p["name"], p["direction"]
            if not p["width"] or p["width"] == 1 and (name, None) in bit_src:
                expr = bit_src.get((name, None))
                if expr is None and p["width"] == 1:
                    lo = min(p["msb"], p["lsb"])
                    expr = bit_src.get((name, lo))
                if expr is None:
                    if direction == "input":
                        expr = "1'b1"
                        warnings.append("输入端口 %s 未分配，tie 1'b1" % name)
                        conns.append("    .%s(%s)" % (name, expr))
                    else:
                        warnings.append("输出端口 %s 未分配，悬空" % name)
                        conns.append("    .%s()" % name)
                else:
                    conns.append("    .%s(%s)" % (name, expr))
                continue
            if p["width"] is None:
                raise ProjectError("BAD_WIDTH",
                                   "端口 %s 位宽不是常量表达式，无法生成 wrapper" % name)
            lo, hi = min(p["msb"], p["lsb"]), max(p["msb"], p["lsb"])
            idxs = list(range(hi, lo - 1, -1))  # msb first in concat
            if direction != "input" and all(
                    (name, i) not in bit_src for i in idxs):
                warnings.append("输出端口 %s 未分配，悬空" % name)
                conns.append("    .%s()" % name)
                continue
            exprs = []
            missing = 0
            for i in idxs:
                expr = bit_src.get((name, i))
                if expr is None:
                    missing += 1
                    if direction == "input":
                        expr = "1'b1"
                    else:
                        raise ProjectError(
                            "PARTIAL_BUS",
                            "输出总线 %s 仅部分分配（%s[%d] 缺引脚）"
                            % (name, name, i))
                exprs.append(expr)
            if missing:
                warnings.append(
                    "输入总线 %s 有 %d 位未分配，补 1'b1" % (name, missing))
            conns.append("    .%s({%s})" % (name, ", ".join(exprs)))
        inst = "%s u_top (\n%s\n);" % (mod["name"], ",\n".join(conns))
        with open(config.WRAPPER_TEMPLATE, "r", encoding="utf-8") as fh:
            tpl = fh.read()
        return tpl.replace("{{instantiation}}", inst), warnings

    def _verilator_root(self):
        argv, cwd = toolchain.wrap_cmd(["verilator", "-getenv", "VERILATOR_ROOT"])
        try:
            out = subprocess.check_output(
                argv, cwd=cwd, universal_newlines=True, timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).strip()
            if out:
                if toolchain.detect() == "wsl":
                    return out  # already a WSL path; used inside WSL commands
                if os.path.isdir(out):
                    return out
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        return "/usr/share/verilator"

    def _assemble(self):
        proj = self._require_project()
        scan = project_service.scan_project(proj["path"])
        top = self._resolve_top(proj, scan)
        self._begin_step("assemble")
        issues, valid = self._validate_pins(proj, scan, top)
        errors = [msg for level, msg in issues if level == "error"]
        for level, msg in issues:
            self._emit_log("assemble", level, msg)
        if errors:
            self._set_step(proj, "assemble", "fail",
                           "Assembler failed: pin assignment errors")
            raise ProjectError("ASSEMBLE_FAIL", errors[0])
        mod = next(m for m in scan["modules"] if m["name"] == top)
        wrapper, warnings = self._gen_wrapper(mod, valid)
        for msg in warnings:
            self._emit_log("assemble", "warn", msg)
        build_dir = self._build_dir(proj)
        out_dir = self._output_dir(proj)
        wrapper_path = os.path.join(build_dir, "DevelopmentBoard.v")
        with open(wrapper_path, "w", encoding="utf-8") as fh:
            fh.write(wrapper)
        self._emit_log("assemble", "info",
                       "生成 %s" % wrapper_path)
        obj_dir = os.path.join(build_dir, "obj_dir")
        src_files = [os.path.join(proj["path"], f) for f in scan["files"]]
        cmd = (["verilator", "-O3", "--Wno-fatal", "--Wno-TIMESCALEMOD",
                "--cc", "--top-module", "DevelopmentBoard",
                "-y", proj["path"], "+incdir+" + proj["path"]]
               + src_files + [wrapper_path, "--Mdir", obj_dir])
        rc, _ = self._run_streaming("assemble", cmd, build_dir)
        if rc != 0 or not os.path.isdir(obj_dir):
            summary = "Assembler failed at verilator stage"
            self._set_step(proj, "assemble", "fail", summary)
            raise ProjectError("ASSEMBLE_FAIL", summary + "（详见 Messages）")
        sof_name = "%s.sof%s" % (top, toolchain.exe_suffix())
        sof_path = os.path.join(out_dir, sof_name)
        if not os.path.exists(config.SIM_CPP):
            self._emit_log("assemble", "warn",
                           "simulator.cpp 不存在（%s），跳过 g++ 链接；"
                           "仅完成 wrapper + verilator 阶段" % config.SIM_CPP)
            summary = ("Assembler: verilator ok; g++ skipped "
                       "(simulator.cpp missing)")
            state_hash = _input_hash(proj["path"], scan["files"],
                                     self._read_qsf(proj), top)
            store = self._set_step(proj, "assemble", "ok", summary, state_hash)
            store["sof"] = None
            self._save_state(proj, store)
            return {"sof": None, "summary": summary,
                    "wrapper": wrapper_path}
        vroot = self._verilator_root()
        model_cpps = sorted(glob.glob(
            os.path.join(obj_dir, "VDevelopmentBoard*.cpp")))
        new_path = sof_path + ".new"
        cmd = (["g++", "-O3",
                "-I", obj_dir,
                "-I", toolchain.join(vroot, "include"),
                "-I", toolchain.join(vroot, "include", "vltstd"),
                os.path.abspath(config.SIM_CPP)]
               + model_cpps
               + [toolchain.join(vroot, "include", "verilated.cpp"),
                  "-o", new_path])
        if toolchain.needs_pthread():
            cmd.append("-pthread")
        rc, _ = self._run_streaming("assemble", cmd, build_dir)
        if rc != 0 or not os.path.exists(new_path):
            summary = "Assembler failed at g++ stage"
            self._set_step(proj, "assemble", "fail", summary)
            raise ProjectError("ASSEMBLE_FAIL", summary + "（详见 Messages）")
        # The .sof name is stable across rebuilds; unload a board running
        # the old image before replacing the file (Windows locks running
        # executables; POSIX would keep the old inode — either way the
        # board must be re-programmed after a rebuild).
        if self._before_sof_replace:
            self._before_sof_replace(sof_path)
        os.replace(new_path, sof_path)
        meta = {
            "name": sof_name, "top": top,
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "family": self.board.get("family"),
            "device": self.board.get("device"),
            "assignments": [{"pin": a["pin"], "port": a["port"]}
                            for a in valid],
        }
        with open(sof_path + ".json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=1)
        summary = ("Assembler: generated %s (%d bytes)"
                   % (sof_name, os.path.getsize(sof_path)))
        state_hash = _input_hash(proj["path"], scan["files"],
                                 self._read_qsf(proj), top)
        sof_info = {"name": sof_name,
                    "size_bytes": os.path.getsize(sof_path),
                    "mtime": os.path.getmtime(sof_path)}
        store = self._set_step(proj, "assemble", "ok", summary, state_hash,
                               extra={"sof": sof_info})
        store["sof"] = sof_name
        self._save_state(proj, store)
        return {"sof": sof_name, "summary": summary,
                "path": sof_path}

    # ---- Compile All ----------------------------------------------------

    def run_all(self):
        results = {}
        results["synthesis"] = self.run_synthesis()
        results["fitter"] = self.run_fitter()
        results["assemble"] = self.run_assemble()
        return results
