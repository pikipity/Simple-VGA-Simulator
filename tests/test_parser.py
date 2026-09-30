#!/usr/bin/env python3
"""Parser (yosys JSON) and stale-QSF pruning tests.

Run from the repo root:

    python tests/test_parser.py      (or: uv run python tests/test_parser.py)

The scan tests need the toolchain (yosys); they are skipped when no
toolchain is available. The QSF pruning tests are pure Python.
Temporary fixture projects are created under tests/.tmp_parser/ and
removed afterwards.
"""
import os
import shutil
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

os.environ.setdefault("VGA_BOARD_NO_BROWSER", "1")
os.environ.setdefault("VGA_BOARD_WATCHDOG_TIMEOUT", "3600")

sys.path.insert(0, REPO_ROOT)

from backend.services import project_service, qsf_service, toolchain  # noqa: E402

TMP = os.path.join(TESTS_DIR, ".tmp_parser")


def writeproj(name, files):
    path = os.path.join(TMP, name)
    os.makedirs(path, exist_ok=True)
    for fname, text in files.items():
        with open(os.path.join(path, fname), "w", encoding="utf-8") as fh:
            fh.write(text)
    return path


def ports_by_name(scan, module):
    mod = next(m for m in scan["modules"] if m["name"] == module)
    return {p["name"]: p for p in mod["ports"]}


@unittest.skipIf(toolchain.detect() is None, "no yosys toolchain available")
class TestYosysScan(unittest.TestCase):
    """project_service.scan_project against real yosys."""

    def test_parameterized_header(self):
        path = writeproj("param", {
            "top.v": "module top #(parameter W = 8, parameter DEPTH = (1<<4)) (\n"
                     "    input wire clk, input wire [W-1:0] din,\n"
                     "    output wire [W-1:0] dout);\n"
                     "    sub #(.W(W)) u (.clk(clk), .din(din), .dout(dout));\n"
                     "endmodule\n",
            "sub.v": "module sub #(parameter W = 8) (\n"
                     "    input wire clk, input wire [W-1:0] din,\n"
                     "    output reg [W-1:0] dout);\n"
                     "    always @(posedge clk) dout <= din;\n"
                     "endmodule\n",
        })
        scan = project_service.scan_project(path)
        self.assertEqual(scan["warnings"], [])
        ports = ports_by_name(scan, "top")
        self.assertEqual(ports["din"]["width"], 8)
        self.assertEqual((ports["din"]["msb"], ports["din"]["lsb"]), (7, 0))
        self.assertIsNone(ports["clk"]["width"])  # scalar
        # sub is instantiated by top -> only top is a top candidate
        self.assertEqual(scan["top_candidates"], ["top"])

    def test_nonansi_header(self):
        path = writeproj("nonansi", {
            "nonansi.v": "module nonansi (a, b);\n"
                         "    input a;\n"
                         "    output [3:0] b;\n"
                         "    assign b = {4{a}};\n"
                         "endmodule\n",
        })
        scan = project_service.scan_project(path)
        ports = ports_by_name(scan, "nonansi")
        self.assertEqual(ports["a"]["direction"], "input")
        self.assertEqual(ports["b"]["direction"], "output")
        self.assertEqual(ports["b"]["width"], 4)

    def test_declared_ranges(self):
        path = writeproj("ranges", {
            "ranges.v": "module ranges (input wire [0:7] upto,\n"
                        "    output wire [16:9] off, input wire scalar);\n"
                        "    assign off = 8'h5A;\n"
                        "endmodule\n",
        })
        ports = ports_by_name(project_service.scan_project(path), "ranges")
        self.assertEqual((ports["upto"]["msb"], ports["upto"]["lsb"]), (0, 7))
        self.assertEqual(ports["upto"]["width"], 8)
        self.assertEqual((ports["off"]["msb"], ports["off"]["lsb"]), (16, 9))
        self.assertEqual(ports["off"]["width"], 8)
        self.assertIsNone(ports["scalar"]["width"])

    def test_cross_file_macro(self):
        path = writeproj("macro", {
            "defs.v": "`define VW 4\n",
            "user.v": "module user (output wire [`VW-1:0] q);\n"
                      "    assign q = {`VW{1'b0}};\n"
                      "endmodule\n",
        })
        ports = ports_by_name(project_service.scan_project(path), "user")
        self.assertEqual(ports["q"]["width"], 4)

    def test_body_localparam_width(self):
        path = writeproj("bodylp", {
            "bodylp.v": "module bodylp (output wire [W-1:0] q);\n"
                        "    localparam W = 6;\n"
                        "    assign q = 6'h2A;\n"
                        "endmodule\n",
        })
        ports = ports_by_name(project_service.scan_project(path), "bodylp")
        self.assertEqual(ports["q"]["width"], 6)

    def test_testbench_excluded(self):
        path = writeproj("tb", {
            "good.v": "module good(input clk, output reg [3:0] q);\n"
                      "    always @(posedge clk) q <= q + 1;\n"
                      "endmodule\n",
            "tb.v": "module tb;\n"
                    "    reg clk = 0;\n"
                    "    initial begin\n"
                    "        $display(\"hi\");\n"
                    "        #100 $finish;\n"
                    "    end\n"
                    "    always #5 clk = ~clk;\n"
                    "endmodule\n",
        })
        scan = project_service.scan_project(path)
        names = [m["name"] for m in scan["modules"]]
        self.assertEqual(names, ["good"])
        self.assertEqual(len(scan["warnings"]), 1)
        self.assertEqual(scan["warnings"][0]["file"], "tb.v")

    def test_syntax_error_excluded(self):
        path = writeproj("bad", {
            "ok.v": "module ok(input a, output b); assign b = a; endmodule\n",
            "bad.v": "module bad (input a output b); assign b = a; endmodule\n",
        })
        scan = project_service.scan_project(path)
        self.assertEqual([m["name"] for m in scan["modules"]], ["ok"])
        self.assertEqual(len(scan["warnings"]), 1)
        self.assertIn("bad.v", scan["warnings"][0]["error"])

    def test_all_bad_raises(self):
        path = writeproj("allbad", {
            "bad.v": "module bad (input a output b); endmodule\n",
        })
        with self.assertRaises(project_service.ProjectError) as ctx:
            project_service.scan_project(path)
        self.assertEqual(ctx.exception.code, "PARSE_FAIL")

    def test_no_verilog(self):
        path = writeproj("empty", {"readme.txt": "nothing here\n"})
        with self.assertRaises(project_service.ProjectError) as ctx:
            project_service.scan_project(path)
        self.assertEqual(ctx.exception.code, "NO_VERILOG")


class TestStaleQsfPrune(unittest.TestCase):
    """qsf_service.prune_stale / assign against renamed-resized ports."""

    PORTS = [
        {"name": "clk", "direction": "input",
         "msb": None, "lsb": None, "width": None},
        {"name": "rgb_1", "direction": "output",
         "msb": 14, "lsb": 0, "width": 15},
        {"name": "rgb_0", "direction": "output",
         "msb": None, "lsb": None, "width": None},
    ]
    QSF = ("set_global_assignment -name TOP_LEVEL_ENTITY top\n"
           "set_location_assignment PIN_E1 -to clk\n"
           "set_location_assignment PIN_B4 -to rgb[0]\n"
           "set_location_assignment PIN_A2 -to rgb[1]\n"
           "set_location_assignment PIN_B5 -to rgb_1[2]\n"
           "set_location_assignment PIN_A6 -to rgb_1[99]\n")

    def test_prune_drops_unknown_and_out_of_range(self):
        text, dropped = qsf_service.prune_stale(self.QSF, self.PORTS)
        dropped_ports = sorted(d["port"] for d in dropped)
        self.assertEqual(dropped_ports, ["rgb[0]", "rgb[1]", "rgb_1[99]"])
        self.assertIn("PIN_E1 -to clk", text)
        self.assertIn("PIN_B5 -to rgb_1[2]", text)
        self.assertNotIn("rgb[0]", text)
        self.assertIn("TOP_LEVEL_ENTITY", text)

    def test_assign_ignores_stale_lines(self):
        board_pins = {"E1", "B4", "A2", "B5", "A6"}
        # rgb[0] occupies PIN_B4 in the stale QSF; assigning rgb_0 there
        # must succeed (stale line pruned, no PIN_CONFLICT).
        text = qsf_service.assign(self.QSF, "B4", "rgb_0",
                                  board_pins, self.PORTS)
        self.assertIn("PIN_B4 -to rgb_0", text)
        self.assertNotIn("rgb[1]", text)

    def test_prune_keeps_everything_when_valid(self):
        qsf = ("set_location_assignment PIN_E1 -to clk\n"
               "set_location_assignment PIN_B5 -to rgb_1[2]\n")
        text, dropped = qsf_service.prune_stale(qsf, self.PORTS)
        self.assertEqual(dropped, [])
        self.assertEqual(text, qsf)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
