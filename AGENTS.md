# Simple VGA Simulator - Agent Guide

## Project Overview

Simple VGA Simulator is an FPGA development simulation environment that provides a virtual VGA display, a reset button, 4 custom buttons, and 5 LEDs for testing Verilog designs without physical hardware.

The simulator uses **Verilator** to compile Verilog code into C++ and **SDL2** (software rendering) for real-time visualization. It is designed for educational purposes, specifically for EIE330 students learning FPGA and VGA controller design.

Two ways to run a simulation:

| Path | Entry Point | Audience |
|------|-------------|----------|
| **GUI Launcher** (recommended) | Flutter app in `gui/` | Students, zero-config |
| **Command Line** | `sim/run_simulation.sh` | CI/CD, advanced users |

## Technology Stack

| Component | Technology |
|-----------|------------|
| HDL Simulation | Verilator |
| Graphics Rendering | SDL2 (software rendering) |
| Simulation Wrapper | C++ (`sim/simulator.cpp`) |
| GUI Launcher | Flutter / Dart (`gui/`) |
| Legacy Helper Tool | Python 3 + tkinter (`sim/PinPlanner.py`) |
| Target Resolution | 640x480 @ 60Hz |
| Color Format | RGB565 (16-bit) |
| System Clock | 50 MHz |

## Project Structure

```
Simple-VGA-Simulator/
├── gui/                            # Flutter GUI Launcher (recommended)
│   ├── lib/                        # Dart source code
│   │   ├── main.dart, app.dart     # Entry point
│   │   ├── models/                 # Data models (dependency, project config, verilog module)
│   │   ├── screens/                # launcher_screen.dart (single-screen UI)
│   │   ├── services/               # Core logic (see "GUI Launcher Architecture")
│   │   ├── state/                  # launcher_state.dart (Provider state)
│   │   └── widgets/                # UI components (cards, log console, etc.)
│   ├── assets/
│   │   ├── sim/                    # simulator.cpp + run_simulation.sh templates
│   │   │                           #   ⚠️ MUST stay in sync with sim/ (see sync rules)
│   │   ├── templates/              # development_board.v.tpl
│   │   └── *.png, *.ico            # App icons
│   ├── Example/                    # RTL-only example copies for GUI testing
│   └── test_gui.ps1                # Windows build helper (project on non-system drive)
├── sim/                            # Core simulator files (CLI path)
│   ├── PinPlanner.py               # Legacy GUI tool (CLI backup for board generation)
│   ├── DevelopmentBoard.v          # Top-level Verilog wrapper template
│   ├── simulator.cpp               # C++ simulation wrapper with SDL2
│   └── run_simulation.sh           # Build and run script
├── Example/                        # Example projects (CLI-ready)
│   ├── Example_1_ColorBar/         # Static color bar demo (RTL/ + sim/)
│   └── Example_2_BallMove/         # Interactive ball movement demo (RTL/ + sim/)
├── SchematicDiagram/               # Documentation diagrams
├── README.md                       # Quick start guide
├── Manual for EIE330 Students.md   # Detailed student manual
└── LICENSE                         # MIT License
```

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (Ubuntu 22.04+) | ✅ Fully supported | Native or VirtualBox VM |
| macOS 15.0+ (Sequoia) | ✅ Fully supported | Intel & Apple Silicon |
| Windows 10/11 (WSL2) | ✅ Supported | GUI falls back to WSL automatically |
| Windows 10/11 (MSYS2) | ✅ Supported | Native Windows, no WSL required |

## Prerequisites

### Simulation Environment (Required)

| Tool | Ubuntu / Debian | macOS | Windows (MSYS2) |
|------|-----------------|-------|-----------------|
| **Verilator** | `sudo apt install verilator` | `brew install verilator` | `pacman -S mingw-w64-x86_64-verilator` |
| **SDL2** | `sudo apt install libsdl2-dev` | `brew install sdl2` | `pacman -S mingw-w64-x86_64-SDL2` |
| **make + g++** | `sudo apt install build-essential` | `xcode-select --install` | `pacman -S make mingw-w64-x86_64-gcc` |

**Verify installation:**
```bash
verilator --version      # Should show 4.0+
sdl2-config --version    # Should show 2.0+
make --version           # Should show 3.81+
g++ --version            # Should show 7.0+
```

#### Ubuntu 22.04 SDL2 Dependency Issue

If `libsdl2-dev` installation fails with version mismatch errors (`libpulse-dev`, `libudev-dev`), the installed libraries are newer than the default repository. Add the official updates repository:

```bash
sudo tee -a /etc/apt/sources.list << 'EOF'
deb http://archive.ubuntu.com/ubuntu jammy-updates main universe
deb http://security.ubuntu.com/ubuntu jammy-security main universe
EOF

sudo apt update
sudo apt install libsdl2-dev
```

#### Windows (WSL2)

1. `wsl --install -d Ubuntu-22.04` (PowerShell as Administrator), restart
2. Inside WSL2: `sudo apt install -y build-essential verilator libsdl2-dev make`
3. Display environment is auto-configured by `run_simulation.sh` (no manual setup)

#### Windows (MSYS2)

1. Install from https://www.msys2.org/
2. In MSYS2 MinGW 64-bit terminal: `pacman -Syu`, then install the packages in the table above
3. Add `C:\tools\msys64\mingw64\bin` and `C:\tools\msys64\usr\bin` to Windows PATH

### GUI Launcher (Optional)

- **Pre-built package (recommended)**: Download from [GitHub Releases](../../releases), extract and run
- **Build from source**: Install Flutter SDK (Stable, 3.0+), then:
  ```bash
  cd gui
  flutter pub get
  flutter run -d windows   # or macos / linux
  ```
- **Windows with project on non-system drive** (e.g. `D:`, `E:`, VBox shared folder): Flutter cannot build across drive letters. Use the helper script:
  ```powershell
  cd gui
  powershell -ExecutionPolicy Bypass -File test_gui.ps1
  ```
  The script creates a proxy project in `C:\Windows\Temp\vga_gui_test`, junctions `lib/` and `assets/`, builds, and launches. Requires **Windows Developer Mode** enabled.

## Build and Run

### GUI Launcher Workflow

1. **Dependency Check** — Verifies Verilator, SDL2, make, g++ (native first, then WSL on Windows)
2. **Select Project Directory** — Folder containing `.v` files; GUI scans and parses modules
3. **Select Top Module** — Signal mapping is auto-inferred, adjustable via dropdowns
4. **Run Simulation** — GUI creates `<RTL>/sim/`, copies templates, generates `DevelopmentBoard.v`, compiles and launches; logs stream to the console and `<RTL>/sim/sim.log`

### CLI Workflow

1. Copy required files to your project's `sim/` directory:
   - `sim/DevelopmentBoard.v` (edit to instantiate your module)
   - `sim/simulator.cpp`
   - `sim/run_simulation.sh`
2. Make the script executable: `chmod +x run_simulation.sh`
3. Run with your RTL directory path:
   ```bash
   ./run_simulation.sh ../RTL    # RTL in parent directory
   ./run_simulation.sh           # RTL in the same directory as the script
   ```

### Build Process Details (run_simulation.sh)

The script performs the following steps:

0. **WSL display auto-config** — If running under WSL and `DISPLAY` is unset, exports `DISPLAY=:0` and sets up `XDG_RUNTIME_DIR` / `WAYLAND_DISPLAY`
1. **Path validation** — Errors out if the script path contains spaces (GNU Make limitation)
2. **SDL2 detection** — Searches `sdl2-config` in PATH, `/opt/homebrew/bin`, `/usr/local/bin`, `/usr/bin`; falls back to `-I/usr/include/SDL2 -lSDL2`
3. **Verilation**:
   ```bash
   verilator -O3 --Wno-fatal --cc --exe -I<rtl_path> simulator.cpp DevelopmentBoard.v \
       -LDFLAGS <sdl_libs> -CFLAGS <sdl_cflags>
   ```
4. **Compilation** — `export CXXFLAGS=<sdl_cflags>` (so make receives SDL headers), then:
   ```bash
   make -j -C obj_dir -f VDevelopmentBoard.mk VDevelopmentBoard
   ```
5. **Execution** — `obj_dir/VDevelopmentBoard`

## Simulator Architecture (sim/simulator.cpp)

### Threading Model

- **Main thread**: SDL initialization, window creation, event loop (`run_event_loop()`)
- **Simulation thread**: `simulation_loop()` — ticks the clock, samples VGA pixels
- Shared state uses `std::atomic` (button states, LED states, buffer pointers, quit flags)
- `cleanup_simulation()` is reentry-safe (atomic guard) and handles thread join + SDL resource release

### Rendering Pipeline

- **Software rendering**: simulation writes RGB float pixels into a double-buffered framebuffer (`buffer_a`/`buffer_b`, x-major layout); no GPU draw calls per pixel
- **Buffer swap**: `sample_pixel()` sets `buffer_swap_pending` on the v_sync rising edge; `render_sdl()` atomically swaps `write_buffer`/`read_buffer` pointers
- **Per frame**: float RGB → `SDL_MapRGB` conversion into a 640×480 `SDL_Surface`, then one `SDL_BlitScaled()` onto the window surface (replaces the old ~300k `glRectf` calls per frame)
- RGB565 → float conversion uses precomputed lookup tables (`RGB5_TO_FLOAT`, `RGB6_TO_FLOAT`)

### Window Layout

Window is created at 800×850 logical pixels with `SDL_WINDOW_ALLOW_HIGHDPI` (actual surface size is read back for HiDPI). Three vertical areas, drawn each frame:

1. **VGA area** — 4:3 aspect maintained, scaled to fit
2. **LED area** — 5 red LEDs with `LED1`–`LED5` labels (5x5 bitmap font)
3. **Button area** — 5 clickable virtual buttons (RESET, B2–B5)

### Input Handling (Virtual Buttons)

Keyboard input was removed (2026-05-02); input is now mouse-based:

| Action | Effect |
|--------|--------|
| Left-click & hold a button | Signal goes to 0 (active low); button drawn green |
| Release left button | Signal returns to 1 |
| Drag mouse out while held | Button auto-releases |
| Click RESET | Also sets `restart_triggered` → simulation re-runs `reset()` |
| `ESC` or `Q` / window close | Quit |

Event loop details: 60 FPS target with adaptive `SDL_Delay`; **at most 1 event is processed per frame** — remaining events in the SDL queue are **drained and discarded** (counted as "dropped" in stats), NOT deferred to the next frame. This was a deliberate trade-off to keep the simulation thread fed on low-core machines, but it means rapid click-release sequences can lose the release event.

### Simulation Timing

**Full speed, no wall-clock pacing.** `wait_10ns()` is a no-op; the simulation thread runs as fast as the CPU allows and calls `std::this_thread::yield()` every 1024 iterations to avoid starving the render thread. (The earlier `RealTimeSync` wall-clock mechanism was removed on 2026-05-02 — see Change History.)

Each iteration: two `tick()` calls (full clock cycles: clk high → eval → clk low → eval) + one `sample_pixel()`.

### VGA Signal Tracking

`sample_pixel()` detects **rising edges** of `h_sync` / `v_sync` (active-high sync as generated by the Verilog examples) and maintains `(coord_x, coord_y)`. Pixels are captured in the active region starting at `H_ACTIVE_START=144`, `V_ACTIVE_START=35`.

### Reset Behavior

`reset()` drives `reset=0` (active-low reset asserted) for 10 clock cycles, then releases to 1; also clears framebuffers, key states, and LED states.

### Statistics Output

Everything goes to **stderr**: per-second EventLoop report (FPS, events processed/dropped, max frame time), VSync counter every 60 frames, input event logs, and final stats on exit. Useful for debugging performance issues.

## GUI Launcher Architecture (gui/)

Single-screen Flutter app (`launcher_screen.dart`) using Provider. State lives in `LauncherState` (`lib/state/launcher_state.dart`).

### Services

| Service | Responsibility |
|---------|----------------|
| `DependencyChecker` | Checks Verilator/SDL2/make/g++; on Windows tries native first, then WSL |
| `VerilogParser` | Scans a directory for `.v` files, parses ANSI-style module ports with regex |
| `WorkspaceService` | Creates `<RTL>/sim/`, copies `assets/sim/` templates (LF-normalized), generates `DevelopmentBoard.v` |
| `BoardGenerator` | Fills `assets/templates/development_board.v.tpl` (`{{module_name}}`, `{{connections}}`) |
| `CompilerService` | Runs `run_simulation.sh` via bash (Windows: native verilator → otherwise WSL with `/mnt/<drive>/` paths); merges stdout/stderr into the log stream |
| `PlatformHelper` | Platform detection, Windows↔WSL path conversion |

### Signal Auto-Inference Rules

Mapping is `board signal → module port`. First match wins; unmatched signals are left empty and can be set manually via dropdowns.

| Board Signal | Candidate Port Names (in order) |
|--------------|--------------------------------|
| `clk` | `clk`, `sys_clk`, `clock`, `sys_clock` |
| `reset` | `reset`, `sys_rst_n`, `rst_n`, `rst`, `sys_reset` |
| `B2`–`B5` | `up`/`down`/`left`/`right`, `b2`–`b5`, `btn2`–`btn5` |
| `h_sync` | `h_sync`, `hsync`, `hs` |
| `v_sync` | `v_sync`, `vsync`, `vs` |
| `rgb` | `rgb`, `vga_rgb`, `data` |
| `led1`–`led5` | `led1`–`led5` |

### Known Parser/Tooling Limitations

- Directory scan is **non-recursive** — `.v` files in subdirectories are not found
- ANSI-style ports only; modules with `#(parameter ...)` headers are not matched
- Port list is split on commas — no support for multi-dimensional ports containing commas
- `stopSimulation()` kills the bash process; on some platforms child processes (make/simulator) may survive briefly

## Development Conventions

### Verilog Coding Requirements

1. **Timescale Directive**: ALL Verilog files MUST include at the beginning:
   ```verilog
   `timescale 1ns / 1ns
   ```

2. **No IP Cores**: The simulator does NOT support vendor IP cores (PLL, RAM blocks, etc.). Replace with your own implementations.

3. **Clock Generation**: Since PLL IP is not supported, use simple clock dividers:
   ```verilog
   reg vga_clk;
   always @(posedge sys_clk or negedge sys_rst_n) begin
       if (!sys_rst_n)
           vga_clk <= 0;
       else
           vga_clk <= ~vga_clk;  // Divides 50MHz to 25MHz
   end
   ```

### Module Interface Standards

Your top-level module should follow this interface pattern (these names are what the GUI auto-inference recognizes):

```verilog
module YourModule(
    input wire sys_clk,      // 50MHz system clock
    input wire sys_rst_n,    // Active-low reset
    input wire up,           // Button input (active low)
    input wire down,         // Button input (active low)
    input wire left,         // Button input (active low)
    input wire right,        // Button input (active low)
    output wire hsync,       // VGA horizontal sync
    output wire vsync,       // VGA vertical sync
    output wire [15:0] rgb,  // RGB565 color output
    output wire led1,        // LED outputs (active low)
    output wire led2,
    output wire led3,
    output wire led4,
    output wire led5
);
```

### DevelopmentBoard.v Modification

CLI users edit `DevelopmentBoard.v` to instantiate their module:

```verilog
YourModule YourModule_inst(
    .sys_clk(clk),
    .sys_rst_n(reset),
    .hsync(h_sync),
    .vsync(v_sync),
    .rgb(rgb),
    .up(B2),
    .down(B3),
    .left(B4),
    .right(B5),
    .led1(led1),
    .led2(led2),
    .led3(led3),
    .led4(led4),
    .led5(led5)
);
```

**DO NOT modify** the `DevelopmentBoard` module header (input/output declarations). GUI users never touch this file — it is generated from `gui/assets/templates/development_board.v.tpl`.

## Input/Output Mapping

### Virtual Buttons

The simulator window displays 5 clickable square buttons at the bottom:

| Button | Signal | Function | Active Level |
|--------|--------|----------|--------------|
| **RESET** | reset | System reset | 0 (held) |
| **B2** | B2 | Custom button 2 | 0 (held) |
| **B3** | B3 | Custom button 3 | 0 (held) |
| **B4** | B4 | Custom button 4 | 0 (held) |
| **B5** | B5 | Custom button 5 | 0 (held) |

> Held button = signal 0. Released = 1. Dragging the mouse off the button while held auto-releases it.

### VGA Specifications

| Parameter | Value |
|-----------|-------|
| Resolution | 640x480 |
| Refresh Rate | 60Hz |
| H_SYNC | 96 cycles |
| H_BACK | 40 cycles |
| H_LEFT | 8 cycles |
| H_VALID | 640 cycles |
| H_RIGHT | 8 cycles |
| H_FRONT | 8 cycles |
| H_TOTAL | 800 cycles |
| V_SYNC | 2 lines |
| V_BACK | 25 lines |
| V_TOP | 8 lines |
| V_VALID | 480 lines |
| V_BOTTOM | 8 lines |
| V_FRONT | 2 lines |
| V_TOTAL | 525 lines |

In `simulator.cpp` these appear as `LEFT_PORCH=48` (H_BACK+H_LEFT), `RIGHT_PORCH=16` (H_RIGHT+H_FRONT), `TOP_PORCH=33` (V_BACK+V_TOP), `BOTTOM_PORCH=10` (V_BOTTOM+V_FRONT), with active region starting at `(144, 35)`. Sync pulses are detected on their **rising edge** (active high).

### RGB565 Color Format

| Bit Range | Color Component |
|-----------|-----------------|
| [15:11]   | Red (5 bits)    |
| [10:5]    | Green (6 bits)  |
| [4:0]     | Blue (5 bits)   |

Example color constants:
```verilog
parameter RED    = 16'hF800;
parameter GREEN  = 16'h07E0;
parameter BLUE   = 16'h001F;
parameter WHITE  = 16'hFFFF;
parameter BLACK  = 16'h0000;
```

## Testing Instructions

### Example 1: Color Bar Test

```bash
cd Example/Example_1_ColorBar/sim
chmod +x run_simulation.sh
./run_simulation.sh ../RTL
```

Expected: Vertical color bars displayed on the VGA screen.

### Example 2: Ball Movement Test

```bash
cd Example/Example_2_BallMove/sim
chmod +x run_simulation.sh
./run_simulation.sh ../RTL
```

Expected: Blue ball on purple background. **Click and hold** the B2/B3/B4/B5 virtual buttons at the bottom of the window to move the ball. Corresponding LEDs light up while buttons are held.

## Troubleshooting

| Error | Solution |
|-------|----------|
| `verilator: command not found` | **Ubuntu:** `sudo apt install verilator`<br>**macOS:** `brew install verilator`<br>**MSYS2:** `pacman -S mingw-w64-x86_64-verilator` |
| `SDL.h: No such file` | **Ubuntu:** `sudo apt install libsdl2-dev`<br>**macOS:** `brew install sdl2`<br>**MSYS2:** `pacman -S mingw-w64-x86_64-SDL2` |
| `obj_dir/VDevelopmentBoard.mk: No such file` | Verilation failed. Check Verilog syntax and include paths |
| `project path contains spaces` | GNU Make limitation — move the project to a path without spaces |
| Black screen / no display | Check VGA timing parameters match the specification; check sync polarity (rising-edge detection) |
| Buttons not responding | Button inputs are active-low (0 while held); click-and-hold, not single-click |
| Button appears stuck | Rapid click-release may drop the release event (1 event/frame limit) — click again |
| WSL: window does not open | `run_simulation.sh` auto-sets `DISPLAY=:0`; verify WSLg or an X server is running |
| Windows GUI: `bash` not found | Install MSYS2 and add to PATH, or install WSL2 (GUI auto-falls-back) |
| Windows GUI: build fails on `D:`/`E:` drive | Use `gui/test_gui.ps1` (cross-drive Flutter build limitation) |
| `error messaging the mach port for IMKCFRunLoopWakeUpReliable` | **macOS + PinPlanner only:** Harmless Input Method Kit warning. Ignore |

## Generated Artifacts

The build process creates an `obj_dir/` directory containing:
- `VDevelopmentBoard` - Compiled simulation executable
- `VDevelopmentBoard.cpp` / `.h` - Verilator-generated model
- `verilated.o` - Verilator runtime object files

GUI runs additionally create `<RTL>/sim/sim.log` (appended per run).

**Note**: `obj_dir/` is gitignored and should not be committed.

## Security Considerations

- The simulation runs with user-level permissions
- No network connectivity in the simulation
- Input is limited to mouse/keyboard events captured by SDL2
- Generated C++ code from Verilator should be reviewed for synthesis before FPGA deployment

## Helper Tools

### PinPlanner (Legacy)

`sim/PinPlanner.py` is the predecessor of the GUI Launcher: a tkinter tool that parses a Verilog module and generates `DevelopmentBoard.v`. Kept as a CLI-environment backup; **new work should target the Flutter GUI**, and PinPlanner bugs are only fixed when they block CLI-only users.

**Usage:** `python3 sim/PinPlanner.py`

**Capabilities:** ANSI port parsing (input/output/inout, multi-bit, comments tolerated), visual signal mapping, allows partial mapping (≥1 signal), generates instance name as `{module_name}_inst`.

> macOS note: `IMKCFRunLoopWakeUpReliable` warnings from file dialogs are harmless.

---

## 开发工作流程规则

### 修改方案确认规则（⚠️ 重要）

**规则：所有修改，先给出详细方案，用户确定方案后再执行！**

- **必须先提供方案**：在执行任何代码修改之前，必须向用户详细说明：
  - 修改的具体内容（改哪些文件、改哪里）
  - 修改的技术方案和理由
  - 可能的影响和风险
  - 预期的结果和验证方式

- **等待用户确认**：只有在用户明确回复 "确认"、"同意"、"执行" 或类似指令后，才能开始执行修改

- **禁止擅自执行**：严禁在用户未确认的情况下直接修改文件，除非是非常明确的、用户已同意的修改

### Testing File Organization

**重要规则：所有测试用的文件必须放在单独的测试目录中。**

- 测试脚本、测试数据、临时文件必须放在 `tests/` 或相关模块的测试目录中
- 禁止在生产代码目录（如 `sim/`、`Example/`）中直接创建测试文件
- 这样可以确保生产环境干净，避免用户混淆哪些是核心文件

### Git 提交规范

**规则：仅在用户明确要求时执行 `git commit`**

- 完成修改后**不要**自动执行 `git commit`
- 等待用户明确说 "commit" 或 "提交" 后再执行
- 在提交前，先使用 `git status` 或 `git diff` 向用户展示变更内容
- 确认用户满意后再执行提交

### ⚠️ Main Branch AGENTS.md 管理规则（重要）

**规则：main branch 禁止包含 AGENTS.md 文件**

- **未来所有合并到 main branch 的操作都必须排除 AGENTS.md**
- main branch 中不应存在 AGENTS.md 文件
- 该规则适用于所有合并方式：Pull Request、merge、cherry-pick 等

**验证方法：**

```bash
git ls-tree HEAD | grep AGENTS.md
# 或
ls AGENTS.md 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

**操作建议：**

```bash
# 方法 A: 合并后删除并 amend
git merge <feature-branch>
git rm AGENTS.md
git commit --amend

# 方法 B: 使用 --no-commit 手动控制
git merge <feature-branch> --no-commit --no-ff
git rm AGENTS.md
git commit
```

### AGENTS.md 更新规则

**规则：仅在用户明确要求时更新 AGENTS.md**

- 完成修改后**不要**自动更新 `AGENTS.md`
- 等待用户明确说 "更新 AGENTS.md" 或类似指令后再执行

### simulator.cpp / run_simulation.sh 同步规范

**规则：修改核心仿真文件后，必须同步所有副本。**

`simulator.cpp` 和 `run_simulation.sh` 存在 **4 份副本**，必须保持一致：

| 位置 | 用途 |
|------|------|
| `sim/` | CLI 主版本（源头） |
| `Example/Example_1_ColorBar/sim/` | Example 1 测试 |
| `Example/Example_2_BallMove/sim/` | Example 2 测试 |
| `gui/assets/sim/` | GUI 分发给用户项目的模板 |

**同步命令：**
```bash
cp sim/simulator.cpp sim/run_simulation.sh Example/Example_1_ColorBar/sim/
cp sim/simulator.cpp sim/run_simulation.sh Example/Example_2_BallMove/sim/
cp sim/simulator.cpp sim/run_simulation.sh gui/assets/sim/
```

**验证一致性：**
```bash
diff sim/simulator.cpp Example/Example_1_ColorBar/sim/simulator.cpp
diff sim/simulator.cpp Example/Example_2_BallMove/sim/simulator.cpp
diff sim/simulator.cpp gui/assets/sim/simulator.cpp
diff sim/run_simulation.sh gui/assets/sim/run_simulation.sh
```

**测试前应先用上述 diff 检查文件一致**，不一致时先同步再测试。

**原因：**
- Example 目录是用户学习的主要入口
- `gui/assets/sim/` 会被复制到每个用户的项目中，过时模板会影响所有 GUI 用户
- 确保所有入口使用统一、最新的模拟器代码

## Change History (Summary)

完整历史见 git log。关键节点：

| 日期 | 变更 |
|------|------|
| 2026-02-17 | GLUT 时代的线程安全修复（原子变量初始化、双缓冲帧缓冲、跨平台退出清理） |
| 2026-02-18 | **OpenGL/GLUT → SDL2 软件渲染迁移**：每帧 30 万+ glRectf 调用 → 单次 SDL_BlitScaled，渲染 CPU 占用大幅下降；窗口关闭行为跨平台统一 |
| 2026-02-18 | 加入 RealTimeSync 墙钟同步，随后为虚拟机性能将仿真时钟 12.5MHz → 3.125MHz |
| 2026-05-02 | **移除 RealTimeSync**（`wait_10ns()` 变为空操作，全速仿真 + 周期性 yield） |
| 2026-05-02 | **键盘输入改为鼠标虚拟按钮**（RESET、B2–B5），窗口扩展为 VGA + LED + 按钮三区布局 |
| 2026-05-02 | 新增 Flutter GUI Launcher（`gui/`）；PinPlanner 降为 legacy 备用工具 |
| 2026-05-04~05 | 界面文本英文化；verilator 命令移除 `-Wall` |
| 2026-06-03 | Windows 支持完善（MSYS2 原生 + WSL2 回退、路径空格检查、WSL 显示自动配置） |

## License

MIT License - Copyright (c) 2025 Ze Wang

## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [SDL2 Documentation](https://wiki.libsdl.org/)
- [Flutter Documentation](https://docs.flutter.dev/)
