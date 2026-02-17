# Simple VGA Simulator - Agent Guide

## Project Overview

Simple VGA Simulator is an FPGA development simulation environment that provides a virtual VGA display, reset button, 4 custom buttons, and 5 LEDs for testing Verilog designs without physical hardware.

This simulator uses **Verilator** to compile Verilog code into C++ and **OpenGL/GLUT** for real-time visualization. It is designed for educational purposes, specifically for EIE330 students learning FPGA and VGA controller design.

## Technology Stack

| Component | Technology |
|-----------|------------|
| HDL Simulation | Verilator |
| Graphics Rendering | OpenGL + GLUT |
| Wrapper Code | C++ |
| Helper Tool | Python 3 + tkinter |
| Target Resolution | 640x480 @ 60Hz |
| Color Format | RGB565 (16-bit) |
| System Clock | 50 MHz |

## Project Structure

```
Simple-VGA-Simulator/
├── sim/                          # Core simulator files (REQUIRED for use)
│   ├── PinPlanner.py             # GUI tool for generating DevelopmentBoard.v
│   ├── DevelopmentBoard.v        # Top-level Verilog wrapper module
│   ├── simulator.cpp             # C++ simulation wrapper with OpenGL
│   └── run_simulation.sh         # Build and run script
├── Example/                      # Example projects
│   ├── Example_1_ColorBar/       # Static color bar demo
│   │   ├── RTL/                  # Verilog source files
│   │   └── sim/                  # Simulation folder with DevelopmentBoard.v
│   └── Example_2_BallMove/       # Interactive ball movement demo
│       ├── RTL/                  # Verilog source files
│       └── sim/                  # Simulation folder
├── SchematicDiagram/             # Documentation diagrams
│   ├── SchematicDiagram.drawio   # Editable diagram
│   └── SchematicDiagram.png      # PNG export
├── README.md                     # Quick start guide
├── Manual for EIE330 Students.md # Detailed student manual
└── LICENSE                       # MIT License
```

## Prerequisites

### System Requirements
- Linux (Ubuntu 22.04 LTS recommended)
- macOS (15.0+ Sequoia, tested on Apple Silicon/Darwin 25.0.0)
- Windows users need VirtualBox with Ubuntu or WSL2 with X11 forwarding

### Required Packages

#### Ubuntu / Linux
```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

For users in mainland China, use Tsinghua mirror for apt sources.

#### macOS
```bash
# Install Xcode Command Line Tools (includes gcc, make, OpenGL/GLUT)
xcode-select --install

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Verilator
brew install verilator
```

**macOS Notes:**
- macOS uses Apple's Clang compiler instead of GCC (invoked via `gcc` alias)
- OpenGL/GLUT frameworks are included with Xcode Command Line Tools
- The `run_simulation.sh` script automatically detects macOS and uses the correct linking flags (`-framework GLUT -framework OpenGL` instead of `-lglut -lGLU -lGL`)
- You may see deprecation warnings for OpenGL/GLUT APIs on macOS 10.9+ and 10.14+ respectively; these are harmless

## Build and Run Commands

### Standard Workflow

1. Copy required files to your project directory:
   - `sim/DevelopmentBoard.v`
   - `sim/simulator.cpp`
   - `sim/run_simulation.sh`

2. Make the script executable:
   ```bash
   chmod +x run_simulation.sh
   ```

3. Run simulation with your RTL directory path:
   ```bash
   ./run_simulation.sh <path_to_rtl_directory>
   ```

   Example (RTL is in parent directory):
   ```bash
   ./run_simulation.sh ../RTL
   ```

   If RTL files are in the same directory as the script:
   ```bash
   ./run_simulation.sh
   ```

### Build Process Steps

The `run_simulation.sh` script performs the following steps:

1. **Step 0: Cleanup** - Removes previous `obj_dir/` build artifacts
2. **Step 1: Verilation** - Compiles Verilog to C++ using:
   ```bash
   verilator -Wall --cc --exe -I<rtl_path> simulator.cpp DevelopmentBoard.v \
       -LDFLAGS -lglut -LDFLAGS -lGLU -LDFLAGS -lGL -LDFLAGS -lpthread
   ```
   > On macOS, the script automatically uses `-framework GLUT -framework OpenGL` instead.
3. **Step 2: Compilation** - Builds executable using make:
   ```bash
   make -j -C obj_dir -f VDevelopmentBoard.mk VDevelopmentBoard
   ```
4. **Step 3: Execution** - Runs the simulation:
   ```bash
   obj_dir/VDevelopmentBoard
   ```

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

Your top-level module should follow this interface pattern:

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

Edit `DevelopmentBoard.v` to instantiate your module:

```verilog
// Instantiate your module
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

**DO NOT modify** the `DevelopmentBoard` module header (input/output declarations).

## Input/Output Mapping

### Keyboard Controls

| Key | Signal | Function | Active Level |
|-----|--------|----------|--------------|
| `a` | reset | System reset | 0 (pressed) |
| `s` | B2 | Custom button 2 | 0 (pressed) |
| `d` | B3 | Custom button 3 | 0 (pressed) |
| `f` | B4 | Custom button 4 | 0 (pressed) |
| `g` | B5 | Custom button 5 | 0 (pressed) |

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

Expected: Vertical color bars displayed on VGA screen.

### Example 2: Ball Movement Test

```bash
cd Example/Example_2_BallMove/sim
chmod +x run_simulation.sh
./run_simulation.sh ../RTL
```

Expected: Blue ball on purple background. Use `s`/`d`/`f`/`g` keys to move the ball. Corresponding LEDs light up when buttons are pressed.

## Troubleshooting

### Common Errors

| Error | Solution |
|-------|----------|
| `verilator: command not found` | **Ubuntu:** `sudo apt install verilator`<br>**macOS:** `brew install verilator` |
| `GL/glut.h: No such file` | **Ubuntu:** `sudo apt install libglu1-mesa-dev freeglut3-dev mesa-common-dev`<br>**macOS:** OpenGL/GLUT is included with Xcode Command Line Tools. Run `xcode-select --install` |
| `GLUT Fatal Error: internal error: NSInternalInconsistencyException` | **macOS only:** GLUT must run on the main thread. Ensure you are using the latest `simulator.cpp` which creates a separate thread for simulation while running GLUT on the main thread. |
| `std::atomic` initialization errors | **macOS only:** macOS libc++ has stricter requirements for atomic initialization. The code has been updated to use `.store()` method instead of aggregate initialization. |
| `obj_dir/VDevelopmentBoard.mk: No such file` | Verilation failed. Check Verilog syntax and include paths |
| Black screen / no display | Check VGA timing parameters match specification |
| Buttons not responding | Ensure button inputs are active-low (0 when pressed) |
| `error messaging the mach port for IMKCFRunLoopWakeUpReliable` | **macOS only:** Harmless system warning from Input Method Kit when using file dialogs. Does not affect PinPlanner functionality. Can be safely ignored. |

### Display Issues on WSL

If using WSL on Windows, ensure X11 forwarding is configured:
1. Install VcXsrv or Xming on Windows host
2. Set `DISPLAY` environment variable in WSL
3. Allow X11 forwarding through Windows Firewall

### macOS Specific Notes

#### Deprecation Warnings
On macOS 10.9+ and 10.14+, you will see deprecation warnings for GLUT and OpenGL APIs. These are expected and can be safely ignored. Apple has deprecated these APIs in favor of Metal, but they remain fully functional.

To suppress these warnings, you can add the following to the compiler flags in the Makefile (inside `obj_dir/VDevelopmentBoard.mk`):
```makefile
CXXFLAGS += -DGL_SILENCE_DEPRECATION
```

#### Thread Model
macOS requires GLUT to run on the main thread. The `simulator.cpp` has been restructured to:
- Run GLUT (`glutMainLoop`) on the **main thread**
- Run the Verilator simulation loop on a **background thread**

This is the opposite of the original Linux design but works correctly on both platforms.

## Generated Artifacts

The build process creates an `obj_dir/` directory containing:
- `VDevelopmentBoard` - Compiled simulation executable
- `VDevelopmentBoard.cpp` - Verilator-generated C++ model
- `VDevelopmentBoard.h` - Verilator-generated header
- `verilated.o` - Verilator runtime object files

**Note**: `obj_dir/` is gitignored and should not be committed.

## Security Considerations

- The simulation runs with user-level permissions
- No network connectivity in the simulation
- Input is limited to keyboard events captured by GLUT
- Generated C++ code from Verilator should be reviewed for synthesis before FPGA deployment

## Helper Tools

### PinPlanner

PinPlanner is a GUI tool for automatically generating `DevelopmentBoard.v` wrapper files.

**Features:**
- Parse Verilog module port definitions (ANSI style supported)
- Visual signal mapping interface
- Auto-generate `DevelopmentBoard.v` with proper signal connections

**Usage:**
```bash
python3 sim/PinPlanner.py
```

**Workflow:**
1. Click "Browse Verilog File" to select your top-level module
2. Use dropdown menus to map module signals to development board pins
3. Click "Save Pins" to save the generated `DevelopmentBoard.v`
4. Copy the file to your project's `sim/` directory and run simulation

**Technical Details:**
- Parser supports `input`/`output`/`inout` directions
- Supports multi-bit declarations `[15:0]`, multi-dimensional arrays
- Newline-insensitive (commas, directions, types can be on separate lines)
- Handles line comments `//` and block comments `/* */`

> **Note for macOS users:** You may see `IMKCFRunLoopWakeUpReliable` warning when using file dialogs. This is a harmless system message and can be safely ignored.

## Development Conventions

### Testing File Organization

**重要规则：所有测试用的文件必须放在单独的测试目录中。**

- 测试脚本、测试数据、临时文件必须放在 `tests/` 或相关模块的测试目录中
- 禁止在生产代码目录（如 `sim/`、`Example/`）中直接创建测试文件
- 这样可以确保生产环境干净，避免用户混淆哪些是核心文件

示例结构：
```
Simple-VGA-Simulator/
├── sim/                    # 核心模拟器文件（仅生产代码）
├── tests/                  # 测试文件目录
│   ├── test_pinplanner.py  # PinPlanner测试脚本
│   └── test_data/          # 测试数据
└── Example/                # 示例项目
```

### Git 提交规范

**规则：仅在用户明确要求时执行 `git commit`**

- 完成修改后**不要**自动执行 `git commit`
- 等待用户明确说 "commit" 或 "提交" 后再执行
- 在提交前，先使用 `git status` 或 `git diff` 向用户展示变更内容
- 确认用户满意后再执行提交

**原因：**
- 避免在用户想要检查修改之前就提交
- 给用户机会审查代码变更
- 让用户控制提交时机和提交信息

### AGENTS.md 更新规则

**规则：仅在用户明确要求时更新 AGENTS.md**

- 完成修改后**不要**自动更新 `AGENTS.md`
- 等待用户明确说 "更新 AGENTS.md" 或类似指令后再执行
- 这是为了避免在用户检查修改之前就更新文档，让用户控制文档更新时机

### Example 测试规范

**规则：使用 Example 测试前，确保 Example/sim 下的文件是最新的**

- 修改 `sim/simulator.cpp` 后，必须同步更新到 `Example/*/sim/simulator.cpp`
- 测试前应检查文件是否一致：
  ```bash
  diff sim/simulator.cpp Example/Example_1_ColorBar/sim/simulator.cpp
  diff sim/simulator.cpp Example/Example_2_BallMove/sim/simulator.cpp
  ```
- 如果不一致，先将最新文件复制到 Example 目录：
  ```bash
  cp sim/simulator.cpp Example/Example_1_ColorBar/sim/
  cp sim/simulator.cpp Example/Example_2_BallMove/sim/
  ```

**原因：**
- Example 目录是用户学习的主要入口
- 过时的 simulator.cpp 会导致用户困惑和错误报告
- 确保所有示例使用统一、最新的模拟器代码

## License

MIT License - Copyright (c) 2025 Ze Wang

## TODO / Future Work

### PinPlanner 

**当前状态**: ✅ **已完成并测试通过**

PinPlanner是一个GUI工具，用于自动解析Verilog模块并生成`DevelopmentBoard.v`包装文件。

#### 1. 测试记录 ✅ 所有测试已通过

**Verilog解析功能测试（ANSI风格）:**

| ID | 描述 | 状态 |
|----|------|------|
| V-01~V-05 | 括号与逗号位置（换行不敏感） | ✅ 通过 |
| V-11~V-20 | 信号方向与类型组合（含inout） | ✅ 通过 |
| V-21~V-24 | 多位宽声明 | ✅ 通过 |
| V-31~V-34 | 多信号同声明（逗号分隔） | ✅ 通过 |
| V-41~V-44 | 注释干扰处理 | ✅ 通过 |
| M-01~M-05 | 映射逻辑验证 | ✅ 通过 |
| G-01~G-06 | 代码生成验证 | ✅ 通过 |

**修复的Bug:**
| ID | 问题 | 修复方案 | 状态 |
|----|------|----------|------|
| B-01 | 缺少inout支持 | 添加inout到方向正则表达式 | ✅ 已修复 |
| B-02 | 关键字残留 | `_extract_signal_name`过滤关键字 | ✅ 已修复 |
| B-03 | 强制完整映射 | 改为允许部分映射（至少1个信号） | ✅ 已修复 |
| B-04 | 实例化名硬编码 | 改为`{module_name}_inst` | ✅ 已修复 |
| - | 映射叠加Bug | `update_mapping()`开头清空`self.mapping` | ✅ 已修复 |
| - | 文件对话框起始目录 | 添加`initialdir=os.getcwd()` | ✅ 已修复 |

**回归测试:**
- ✅ Example/ColorBar.v 解析正确
- ✅ Example/Simple_VGA.v 解析正确
- ✅ 生成代码可通过Verilator编译

#### 2. 待改进项目

以下是代码审查后确定的改进项，按优先级分类：

##### 🔴 高优先级（Bug 修复 & 代码质量）

| ID | 问题 | 描述 | 位置 | 状态 |
|----|------|------|------|------|
| I-01 | 命名与功能不符 | 类名 `VerilogTestbenchGenerator` 和窗口标题 "Verilog Testbench Generator" 与工具实际功能（引脚映射）不符，易误导用户以为是生成 Testbench 的工具 | 第7-9行 | ✅ 已修复 |
| I-02 | 残留大量注释代码 | 约有 200 行被注释的旧代码（第72-143、280-329、441-527行），严重影响代码可读性，应删除或使用 Git 管理历史 | 多处 | ✅ 已修复 |
| I-03 | 文件对话框行为不一致 | `askopenfilename` 缺少 `initialdir=os.getcwd()`，与 `askdirectory` 行为不一致，影响用户体验 | 第163行 | ✅ 已修复 |
| I-04 | 生成代码缩进混乱 | 生成的 Verilog 代码混用 Tab 和空格，且缩进层级不统一，影响代码美观 | `generate_testbench_code()` | ✅ 已修复 |

**详细说明：**

**I-01 命名问题：**
- 当前类名：`VerilogTestbenchGenerator`
- 建议改为：`PinPlanner`
- 当前窗口标题：`"Verilog Testbench Generator"`
- 建议改为：`"Pin Planner"`

**I-02 注释代码位置：**
```
第 72-143 行：旧的 GUI 布局代码
第 280-329 行：旧的映射方法（map_signals, clear_mapping, update_mappings_display）
第 441-527 行：旧的 Testbench 生成代码
```

**I-03 文件对话框问题：**
```python
# 当前代码（第163行）：
filename = filedialog.askopenfilename(
    title="Select Verilog Module File",
    filetypes=[("Verilog files", "*.v"), ("All files", "*.*")]
)

# 应统一添加 initialdir：
filename = filedialog.askopenfilename(
    title="Select Verilog Module File",
    filetypes=[("Verilog files", "*.v"), ("All files", "*.*")],
    initialdir=os.getcwd()
)
```

**I-04 缩进问题示例：**
```verilog
# 当前生成的代码混用 Tab 和空格：
module DevelopmentBoard(
    input wire clk, //50MHz      # 空格缩进
    input wire reset, B2, B3, B4, B5,
		 // reset is "a"           # Tab 缩进（混乱）
```

##### 🟡 中优先级（界面问题）

| ID | 问题 | 描述 | 位置 | 状态 |
|----|------|------|------|------|
| I-05 | 界面布局问题 | 映射区域使用 `place()` 绝对定位（`relx=.5, rely=.5`），窗口缩小时内容被截断；信号数量多时没有滚动条，可能超出屏幕 | 第56-57行 | ✅ 已修复 |

**I-05 界面问题详情：**
```python
# 当前代码：
mapping_frame = ttk.Frame()
mapping_frame.place(in_=main_frame, anchor="c", relx=.5, rely=.5)
```

**问题：**
- 使用绝对定位导致窗口缩放时内容被裁剪
- 当模块信号数量很多时，下拉框列表超出屏幕高度，没有滚动条
- 建议改用 `grid()` 或 `pack()` 布局，并添加 `Canvas` + `Scrollbar` 支持

**修复后的附加改进：**
| ID | 问题 | 描述 | 状态 |
|----|------|------|------|
| I-06 | 鼠标滚轮支持不完善 | 原使用 `bind_all` 捕获全局事件，且不支持 Linux；修复后使用 `canvas.bind()` 并添加跨平台支持（Windows/macOS/Linux） | ✅ 已修复 |


### Simulator (sim/simulator.cpp)

**当前状态**: ⚠️ **存在数据竞争等 Bug，需要修复**

Simulator 是核心 C++ 仿真程序，使用 Verilator 编译 Verilog 并通过 OpenGL/GLUT 显示。经代码审查发现多处线程安全问题。

#### 1. 确定会产生 Bug 的问题（需立即修复）

##### 🔴 P0 - 原子数组未初始化

| 项目 | 详情 |
|------|------|
| **位置** | 第61行 `leds_state[5]`，第161行 `keys[5]` |
| **问题** | `std::atomic<int>` 默认构造函数不初始化，读取时得到随机垃圾值 |
| **Bug 表现** | LED 随机闪烁，按键初始状态随机（可能表现为"虚拟按键按下"） |
| **修复方案** | 声明时初始化：`std::atomic<int> keys[5] = {{1}, {1}, {1}, {1}, {1}};` |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前
std::atomic<int> leds_state[5]; // 初始状态在 reset() 中设置
std::atomic<int> keys[5];

// 修改后
std::atomic<int> leds_state[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态
std::atomic<int> keys[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态
```
**测试结果：** ✅ 编译通过，执行正常

##### 🔴 P0 - `gl_setup_complete` 非原子类型

| 项目 | 详情 |
|------|------|
| **位置** | 第30行声明，第215行写入，第407行读取 |
| **问题** | 多线程访问非原子 `bool`，存在数据竞争 |
| **Bug 表现** | 1) 编译器优化可能导致无限循环；2) CPU 缓存不一致导致死等 |
| **修复方案** | 改为 `std::atomic<bool>`，使用 `memory_order_release/acquire` |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前
bool gl_setup_complete = false;
// ...
gl_setup_complete = true;
// ...
while(!gl_setup_complete);

// 修改后
std::atomic<bool> gl_setup_complete{false};
// ...
gl_setup_complete.store(true, std::memory_order_release);
// ...
while (!gl_setup_complete.load(std::memory_order_acquire)) {
    std::this_thread::yield();
}
```
**测试结果：** ✅ 编译通过，执行正常
**选择方案：** 方案B（`release/acquire` 内存序），性能最优且语义正确

##### 🔴 P0 - `restart_triggered` 非原子类型

| 项目 | 详情 |
|------|------|
| **位置** | 第58行声明，第167行写入，第417行读取，第354行写入 |
| **问题** | 主线程写入、模拟线程读取，无同步机制 |
| **Bug 表现** | 1) 重启信号丢失（缓存不一致）；2) 竞态条件导致重复重置 |
| **修复方案** | 改为 `std::atomic<bool>`，使用 `exchange()` 原子读取并清除 |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前
bool restart_triggered = false;
// ... 写入
restart_triggered = true;
// ... 读取并清除（非原子，有竞态窗口）
if (restart_triggered) {
    reset();
}
restart_triggered = false;

// 修改后
std::atomic<bool> restart_triggered{false};
// ... 写入
restart_triggered.store(true, std::memory_order_release);
// ... 原子读取并清除（无竞态窗口）
if (restart_triggered.exchange(false, std::memory_order_acquire)) {
    reset();
}
```
**测试结果：** ✅ 编译通过，执行正常
**选择方案：** 方案B（`exchange()`），原子性读取并清除，彻底消除竞态窗口

##### 🔴 P1 - `graphics_buffer` 无线程同步

| 项目 | 详情 |
|------|------|
| **位置** | 第50行声明，第392-394行写入，第99行读取 |
| **问题** | 模拟线程写入、GLUT 渲染线程读取，无同步机制 |
| **Bug 表现** | 1) 画面撕裂（读取半新半旧帧）；2) RGB 通道不一致（颜色错误） |
| **修复方案** | 实现双缓冲机制，使用原子指针交换 |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前 - 单缓冲，无同步
float graphics_buffer[ACTIVE_WIDTH][ACTIVE_HEIGHT][3] = {};

// 修改后 - 双缓冲，原子指针交换
static float buffer_a[ACTIVE_WIDTH * ACTIVE_HEIGHT * 3] = {};
static float buffer_b[ACTIVE_WIDTH * ACTIVE_HEIGHT * 3] = {};
static std::atomic<float*> write_buffer{buffer_a};  // 模拟线程写入
static std::atomic<float*> read_buffer{buffer_b};   // GLUT线程读取
static std::atomic<bool> buffer_swap_pending{false}; // 新帧就绪标记

// 模拟线程 (sample_pixel): 写入 write_buffer，v_sync时标记交换
// GLUT线程 (render): 检查标记，原子交换指针，读取 read_buffer
```
**选择方案：** 方案B（双缓冲+原子指针交换）
- 零拷贝交换，性能最优
- 无互斥锁，读写互不阻塞
- 垂直同步触发交换，避免画面撕裂
**测试结果：** ✅ 编译通过，执行正常

##### 🟡 P2 - `glutMainLoop()` 不返回导致线程泄漏

| 项目 | 详情 |
|------|------|
| **位置** | 第219行调用，第443行 `join()` |
| **问题** | 某些 GLUT 实现窗口关闭时直接调用 `exit()`，不返回 |
| **Bug 表现** | `sim_thread.join()` 永不执行，资源未释放，模拟线程被强制终止 |
| **修复方案** | 添加全局退出标志 + `glutCloseFunc` 回调 + `atexit()` |
| **状态** | ✅ **已修复（部分）- 跨平台方案** |

**修复日期：** 2026-02-17

**跨平台实现方案：**

| 平台 | GLUT 实现 | 处理方式 | 退出机制 |
|------|-----------|----------|----------|
| **macOS** | 原生 Cocoa | `atexit(cleanup_simulation)` | `exit(0)` 触发清理 |
| **Linux** | freeglut | `glutCloseFunc()` + `glutLeaveMainLoop()` | 窗口关闭回调 |

**关键代码实现：**

```cpp
// 平台检测
#if defined(__APPLE__)
    #define PLATFORM_MACOS 1
#else
    #define PLATFORM_LINUX 1
#endif

// 全局退出标志和线程句柄
static std::atomic<bool> g_quit_requested{false};
static std::thread g_sim_thread;

// 清理函数
void cleanup_simulation() {
    g_quit_requested.store(true, std::memory_order_release);
    if (g_sim_thread.joinable()) {
        g_sim_thread.join();
    }
}

// Linux 窗口关闭回调
#ifdef PLATFORM_LINUX
void window_close_handler() {
    cleanup_simulation();
    glutLeaveMainLoop();
}
#endif

// 键盘退出处理（ESC 或 Q）
void keyPressed(unsigned char key, int x, int y) {
    // ... 原有按键处理 ...
    case 27:  // ESC
    case 'q':
    case 'Q':
        cleanup_simulation();
#if defined(PLATFORM_LINUX)
        glutLeaveMainLoop();
#elif defined(PLATFORM_MACOS)
        exit(0);  // 触发 atexit
#endif
        break;
}

// graphics_loop 平台差异化设置
void graphics_loop(int argc, char** argv) {
    // ... GLUT 初始化 ...
    
#if defined(PLATFORM_MACOS)
    atexit(cleanup_simulation);  // macOS: glutMainLoop 永不返回
#elif defined(PLATFORM_LINUX)
    #ifdef GLUT_ACTION_ON_WINDOW_CLOSE
        glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION);
    #endif
    #ifdef GLUT_HAS_CLOSE_CALLBACK
        glutCloseFunc(window_close_handler);
    #endif
#endif

    glutMainLoop();
}
```

**模拟线程退出检查：**
```cpp
void simulation_loop() {
    // ... 初始化 ...
    while (!Verilated::gotFinish() && !g_quit_requested.load(std::memory_order_acquire)) {
        // 模拟循环
    }
    // 清理
    display->final();
    delete display;
}
```

**macOS 窗口关闭按钮问题：**

**状态：** ✅ **已修复**

原生 macOS GLUT 窗口关闭按钮默认可点击但无响应。通过添加 `atexit()` 处理程序，当用户：
1. 点击窗口关闭按钮（触发 `exit()`）
2. 按 `Cmd+Q`（触发 `exit()`）
3. 按 `ESC` 或 `Q` 键（代码中调用 `exit(0)`）

都会执行 `cleanup_simulation()`，优雅地停止模拟线程。

**测试结果：** ✅ macOS 关闭按钮、ESC/Q 键退出均正常工作

#### 2. 可选改进项（建议修复）

##### 🟡 P2 - `wait_10ns()` 实现不可靠 → Wall Clock 实时同步

| 项目 | 详情 |
|------|------|
| **位置** | 第16-20行 |
| **当前问题** | 空循环实现，时序不准确，受 CPU 频率影响 |
| **改进方案** | 实现 `RealTimeSync` 类，基于挂钟时间同步 |
| **适用场景** | 需要真实时序模拟（如 VGA 时序合规性验证） |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前 - 空循环
void wait_10ns() {
    for (volatile int i = 0; i < 100; ++i) {}
}

// 修改后 - Wall Clock 同步
class RealTimeSync {
    std::chrono::steady_clock::time_point epoch;
    uint64_t sim_cycles = 0;
    static constexpr uint64_t NS_PER_CYCLE = 20;  // 50MHz = 20ns/cycle
    
public:
    RealTimeSync() : epoch(std::chrono::steady_clock::now()) {}
    
    void tick() {
        sim_cycles++;
        uint64_t target_ns = sim_cycles * NS_PER_CYCLE;
        
        auto now = std::chrono::steady_clock::now();
        auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            now - epoch).count();
        
        if (target_ns > elapsed_ns) {
            // 忙等待直到真实时间追上仿真时间
            auto target = now + std::chrono::nanoseconds(target_ns - elapsed_ns);
            while (std::chrono::steady_clock::now() < target) {
                #if defined(__x86_64__)
                __builtin_ia32_pause();  // 降低功耗
                #endif
            }
        } else if (elapsed_ns - target_ns > 1000000) {
            // 滞后超过1ms时输出警告
            std::cerr << "Simulation lag: " << (elapsed_ns - target_ns) << "ns\n";
        }
    }
};

static RealTimeSync g_sync;
void wait_10ns() { g_sync.tick(); }
```
**选择方案：** 方案C（Wall Clock）
- 精确同步真实时间和仿真时间
- 可检测电脑性能是否足够
- x86_64 使用 `pause` 指令降低功耗
**测试结果：** ✅ 编译通过，执行正常，实时同步工作

**后续修复 - "Simulation lag" 警告过多：**

| 项目 | 详情 |
|------|------|
| **问题** | 启动时 `RealTimeSync` epoch 在程序启动时设置，而仿真线程需要等待 GLUT 初始化（数秒），导致大量虚假滞后警告 |
| **解决方案** | 添加 `reset()` 方法，在初始化完成后重置时间基准 |
| **代码** | `void reset() { epoch = steady_clock::now(); sim_cycles = 0; }` |
| **调用点** | `simulation_loop()` 中 `reset()` 之后调用 `g_sync.reset()` |
| **状态** | ✅ **已修复** |

**说明：** 性能不足时 "Simulation lag" 刷屏是预期行为，让用户了解性能状况。如需减少输出，可降低仿真时钟频率或关闭实时同步。

##### 🟢 P3 - `display` 原始指针异常不安全

| 项目 | 详情 |
|------|------|
| **位置** | 第22行声明，第410行 `new`，第429行 `delete` |
| **问题** | 异常抛出时 `delete` 不会执行，可能内存泄漏 |
| **改进方案** | 改为 `std::unique_ptr<VDevelopmentBoard>` |
| **状态** | ⚠️ **无法修复 - 与 P1 冲突** |

**问题分析：**
使用 `std::unique_ptr` 确实更安全，但在 macOS 上存在致命问题：

1. `glutMainLoop` 在 macOS 上可能直接调用 `exit()` 终止程序
2. 程序退出时会调用全局变量 `display` (unique_ptr) 的析构函数
3. 同时 `simulation_loop` 线程可能还在运行并访问 `display`
4. 导致 **段错误**（主线程释放内存，子线程正在访问）

**测试验证：**
```cpp
std::unique_ptr<VDevelopmentBoard> display;
// ...
display.reset(new VDevelopmentBoard());
// ...
display->final();
display.reset();
```
结果：运行一段时间后 `Segmentation fault: 11`

**原始代码为什么安全：**
原始代码使用原始指针，不主动释放内存。程序退出时即使有内存泄漏，也不会触发段错误。

**结论：** 在 P1（线程泄漏）无法修复的前提下，P3 也无法安全实现。保持原始指针实现。

##### 🟢 P3 - 删除注释代码

| 项目 | 详情 |
|------|------|
| **位置** | `discard_input()` 函数、旧按键处理逻辑、调试代码等 |
| **问题** | 约 100+ 行注释代码影响可读性 |
| **改进方案** | 删除旧代码，保留功能性注释 |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
- 删除 `discard_input()` 函数（已注释）
- 删除 `apply_input()` 内的旧按键边缘检测逻辑（已注释）
- 删除 `sample_pixel()` 内的调试代码（已注释）
- 删除 `tick()` 内的旧上升沿代码（已注释）
- 清理 `reset()` 内的旧注释和未使用的 `key_prev_state` 引用
- 统一注释风格为中英文混合（保留中文注释用于教学目的）
**测试结果：** ✅ 编译通过，执行正常

##### 🟢 P3 - RGB565 转换优化

| 项目 | 详情 |
|------|------|
| **位置** | 第392-394行 |
| **问题** | 每次像素 3 次浮点除法，效率低 |
| **改进方案** | 预计算查找表 `RGB5_TO_FLOAT[32]` 和 `RGB6_TO_FLOAT[64]` |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
```cpp
// 修改前 - 每次像素 3 次浮点除法
buf[idx] = float((rgb & 0xF800) >> 11) / 31.0f;
buf[idx + 1] = float((rgb & 0x07E0) >> 5) / 63.0f;
buf[idx + 2] = float((rgb & 0x001F)) / 31.0f;

// 修改后 - 查找表 O(1) 访问
static float RGB5_TO_FLOAT[32];   // 5-bit -> float
static float RGB6_TO_FLOAT[64];   // 6-bit -> float

// 初始化（只需一次）
void init_rgb_lookup_tables() {
    for (int i = 0; i < 32; i++) RGB5_TO_FLOAT[i] = float(i) / 31.0f;
    for (int i = 0; i < 64; i++) RGB6_TO_FLOAT[i] = float(i) / 63.0f;
}

// 像素转换
buf[idx] = RGB5_TO_FLOAT[(rgb >> 11) & 0x1F];      // Red
buf[idx + 1] = RGB6_TO_FLOAT[(rgb >> 5) & 0x3F];   // Green
buf[idx + 2] = RGB5_TO_FLOAT[rgb & 0x1F];          // Blue
```
**优化效果：** 消除 90 万次/帧浮点除法，替换为缓存友好的查表
**选择方案：** 方案A（预计算查找表）
**测试结果：** ✅ 编译通过，执行正常

##### 🟢 P3 - Tab/空格缩进混用

| 项目 | 详情 |
|------|------|
| **位置** | 多处（常量定义、case语句、空行） |
| **问题** | Tab 和空格混用，不同编辑器显示不一致 |
| **改进方案** | 统一使用 4 空格缩进 |
| **状态** | ✅ **已修复** |

**修复日期：** 2026-02-17
**修复内容：**
- 将所有 Tab 字符 (`\t`) 替换为 4 个空格
- 清理多余的连续空行
- 统一常量定义的对齐方式
**测试结果：** ✅ 编译通过，执行正常

#### 3. 跨平台兼容性说明

| 平台 | 状态 | 备注 |
|------|------|------|
| **macOS Intel (x86_64)** | ✅ 完全支持 | `__builtin_ia32_pause()` 优化 |
| **macOS Apple Silicon (ARM64)** | ✅ 完全支持 | `__asm__("yield")` 优化 |
| **Linux (x86_64)** | ✅ 完全支持 | `__builtin_ia32_pause()` 优化 |
| **Linux (ARM64)** | ✅ 支持 | `__asm__("yield")` 优化 |
| **Windows (WSL2)** | ✅ 支持 | 等同于 Linux |

**跨平台修复记录：**
```cpp
// 忙等待循环的跨平台优化
while (std::chrono::steady_clock::now() < target) {
    #if defined(__x86_64__)
        __builtin_ia32_pause();           // Intel/AMD x86_64
    #elif defined(__aarch64__) || defined(_M_ARM64)
        __asm__ __volatile__("yield");    // ARM64 (Apple Silicon, etc.)
    #endif
}
```

#### 4. 修复优先级总结

| 优先级 | 问题 | 修复难度 | 不修复的后果 |
|--------|------|----------|--------------|
| 🔴 P0 | 原子数组未初始化 | 极低 | 随机闪烁/按键异常 |
| 🔴 P0 | `gl_setup_complete` 非原子 | 低 | 程序随机卡住 |
| 🔴 P0 | `restart_triggered` 非原子 | 低 | 重启功能失效 |
| 🔴 P1 | `graphics_buffer` 无同步 | 中 | 画面撕裂/颜色错误 |
| ✅ P2 | `glutMainLoop` 跨平台退出 | 中 | 线程泄漏（已修复）|
| 🟡 P2 | Wall Clock 实时同步 | 低 | 时序不准确 |
| ✅ P2 | macOS 窗口关闭按钮 | 低 | 无法退出（已修复）|
| 🟢 P3 | 其他代码质量问题 | 低-中 | 维护困难 |

---

## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [OpenGL/GLUT Documentation](https://www.opengl.org/)
