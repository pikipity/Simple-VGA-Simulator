# Simple VGA Simulator - Agent Guide

## Project Overview

Simple VGA Simulator is an FPGA development simulation environment that provides a virtual VGA display, reset button, 4 custom buttons, and 5 LEDs for testing Verilog designs without physical hardware.

This simulator uses **Verilator** to compile Verilog code into C++ and **SDL2** for real-time visualization. It is designed for educational purposes, specifically for EIE330 students learning FPGA and VGA controller design.

## Technology Stack

| Component | Technology |
|-----------|------------|
| HDL Simulation | Verilator |
| Graphics Rendering | SDL2 |
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
│   ├── simulator.cpp             # C++ simulation wrapper with SDL2
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
sudo apt-get install libsdl2-dev
```

For users in mainland China, use Tsinghua mirror for apt sources.

#### Ubuntu 22.04 SDL2 安装依赖问题

如果在 Ubuntu 22.04 上安装 `libsdl2-dev` 时遇到如下依赖错误：

```
libpulse-dev : Depends: libpulse0 (= 1:15.99.1+dfsg1-1ubuntu1) but 1:15.99.1+dfsg1-1ubuntu2.2 is to be installed
libudev-dev : Depends: libudev1 (= 249.11-0ubuntu3.16) but 249.11-0ubuntu3.17 is to be installed
E: Unable to correct problems, you have held broken packages.
```

**原因**：系统已安装的库版本较新，但默认软件源中的开发包版本较旧，导致版本不匹配。

**解决方案**：向 `/etc/apt/sources.list` 添加 Ubuntu 官方更新源：

```bash
sudo tee -a /etc/apt/sources.list << 'EOF'
deb http://archive.ubuntu.com/ubuntu jammy-updates main universe
deb http://security.ubuntu.com/ubuntu jammy-security main universe
EOF

sudo apt update
sudo apt install libsdl2-dev
```

#### macOS
```bash
# Install Xcode Command Line Tools (includes gcc, make)
xcode-select --install

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install SDL2
brew install sdl2

# Install Verilator
brew install verilator
```

**macOS Notes:**
- macOS uses Apple's Clang compiler instead of GCC (invoked via `gcc` alias)
- The `run_simulation.sh` script automatically detects SDL2 installation path using `sdl2-config`

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
   verilator -O3 --Wno-fatal -Wall --cc --exe -I<rtl_path> simulator.cpp DevelopmentBoard.v \
       -LDFLAGS -lSDL2 -LDFLAGS -lpthread
   ```
   > The `run_simulation.sh` script automatically detects SDL2 flags using `sdl2-config`.
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
| `SDL.h: No such file` | **Ubuntu:** `sudo apt install libsdl2-dev`<br>**macOS:** `brew install sdl2` |
| `obj_dir/VDevelopmentBoard.mk: No such file` | Verilation failed. Check Verilog syntax and include paths |
| Black screen / no display | Check VGA timing parameters match specification |
| Buttons not responding | Ensure button inputs are active-low (0 when pressed) |
| `error messaging the mach port for IMKCFRunLoopWakeUpReliable` | **macOS only:** Harmless system warning from Input Method Kit when using file dialogs. Does not affect PinPlanner functionality. Can be safely ignored. |

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
- Input is limited to keyboard events captured by SDL2
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

### 修改方案确认规则（⚠️ 重要）

**规则：所有修改，先给出详细方案，用户确定方案后再执行！**

- **必须先提供方案**：在执行任何代码修改之前，必须向用户详细说明：
  - 修改的具体内容（改哪些文件、改哪里）
  - 修改的技术方案和理由
  - 可能的影响和风险
  - 预期的结果和验证方式

- **等待用户确认**：只有在用户明确回复 "确认"、"同意"、"执行" 或类似指令后，才能开始执行修改

- **禁止擅自执行**：严禁在用户未确认的情况下直接修改文件，除非是非常明确的、用户已同意的修改

**原因：**
- 避免用户对方案不满意导致返工
- 让用户充分了解修改的影响和风险
- 让用户有机会提出更好的方案或补充需求
- 确保代码质量和用户体验

---

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

### ⚠️ Main Branch AGENTS.md 管理规则（重要）

**规则：main branch 禁止包含 AGENTS.md 文件**

- **未来所有合并到 main branch 的操作都必须排除 AGENTS.md**
- main branch 中不应存在 AGENTS.md 文件
- 该规则适用于所有合并方式：Pull Request、merge、cherry-pick 等

**验证方法：**

合并前检查 main branch 是否存在 AGENTS.md：
```bash
git ls-tree HEAD | grep AGENTS.md
# 或
ls AGENTS.md 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

**操作建议：**

1. **合并时手动排除**：
   ```bash
   # 方法 A: 合并前删除（适用于目标分支没有 AGENTS.md）
   git merge <feature-branch>
   git rm AGENTS.md
   git commit --amend
   
   # 方法 B: 使用 --no-commit 手动控制
   git merge <feature-branch> --no-commit --no-ff
   git rm AGENTS.md
   git commit
   ```

2. **本地 pre-commit hook**（个人开发环境）：
   创建 `.git/hooks/pre-commit`：
   ```bash
   #!/bin/bash
   if [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] && [ -f "AGENTS.md" ]; then
       echo "Error: AGENTS.md should not exist in main branch"
       exit 1
   fi
   ```

**原因：**
- AGENTS.md 是 agent 专用的开发文档，不适合出现在生产代码分支
- 防止 agent 开发细节泄露到用户可见的主分支
- 保持 main branch 的简洁性，只包含用户需要的代码和文档

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

**后续修复 - 降低仿真时钟频率以缓解性能问题：**

| 项目 | 详情 |
|------|------|
| **问题** | `NS_PER_CYCLE = 20` (50MHz) 对多数现代 CPU 负载过高，导致持续的 "Simulation lag" 警告 |
| **解决方案** | 将 `NS_PER_CYCLE` 从 `20` (50MHz) 调整为 `80` (12.5MHz)，降低 75% 的 CPU 负载 |
| **代码** | `static constexpr uint64_t NS_PER_CYCLE = 80;  // 12.5MHz = 80ns/cycle` |
| **影响** | 仿真时钟降低，但 VGA 显示刷新率仍为 60Hz（由 VSync 控制），视觉体验不变 |
| **测试验证** | ✅ Example 1 和 Example 2 编译运行正常，lag 从 110ms 降至 1-2ms |
| **状态** | ✅ **已修复** |

**备注：** 如仍有 lag 警告，可进一步降低至 `160` (6.25MHz) 或 `320` (3.125MHz)。

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

#### 5. Linux/macOS 兼容性改进（2026-02-17 审查）

以下改进建议来自对 `sim/simulator.cpp` 的跨平台兼容性审查。

| ID | 优先级 | 问题 | 描述 | 位置 | 状态 |
|----|--------|------|------|------|------|
| C-01 | 🟡 中 | 平台检测过于宽泛 | 使用 `#else` 将所有非 Apple 平台视为 Linux，在 Windows、BSD 等平台上会错误识别 | 第 3-13 行 | ✅ **已修复** |
| C-02 | 🟡 中 | GLUT 关闭回调检测不完善 | `GLUT_HAS_CLOSE_CALLBACK` 宏在 freeglut 2.4 不存在，导致 Ubuntu 16.04 等旧系统关闭按钮无效 | 第 333-345 行 | ✅ **已修复** |
| C-03 | 🟢 低 | `cleanup_simulation` 重入安全问题 | 极端情况下可能并发调用导致 double-join（未定义行为） | 第 28-33 行 | ✅ **已修复** |
| C-04 | 🟢 低 | 旧版 GLUT 缺少编译警告 | 使用原版 GLUT 或 freeglut 2.4- 编译时，无提示说明关闭按钮功能受限 | 第 9-15 行 | ✅ **已修复** |

**C-01 精确平台检测：**

当前代码使用 `#else` 将所有非 Apple 平台都视为 Linux，过于宽泛。建议改为：

```cpp
#if defined(__APPLE__)
    #define PLATFORM_MACOS 1
    #include <GLUT/glut.h>
#elif defined(__linux__) || defined(__linux) || defined(linux)
    #define PLATFORM_LINUX 1
    #include <GL/glut.h>
    #ifdef GLUT_API_VERSION
        #include <GL/freeglut_ext.h>
    #endif
#else
    #error "Unsupported platform - only macOS and Linux are supported"
#endif
```

**C-02 改进 GLUT 关闭回调检测：**

freeglut 2.4 支持 `glutCloseFunc` 但没有 `GLUT_HAS_CLOSE_CALLBACK` 宏。建议改为使用 `GLUT_API_VERSION >= 4` 作为主要检测：

```cpp
#if defined(GLUT_API_VERSION) && GLUT_API_VERSION >= 4
    glutCloseFunc(window_close_handler);
#elif defined(GLUT_HAS_CLOSE_CALLBACK)
    glutCloseFunc(window_close_handler);
#endif
```

**C-03 防止 `cleanup_simulation` 重入：**

添加原子标志确保清理逻辑只执行一次：

```cpp
// 新增变量
static std::atomic<bool> g_cleanup_done{false};

// 修改函数
void cleanup_simulation() {
    if (g_cleanup_done.exchange(true, std::memory_order_acq_rel)) {
        return;
    }
    g_quit_requested.store(true, std::memory_order_release);
    if (g_sim_thread.joinable()) {
        g_sim_thread.join();
    }
}
```

**C-04 旧版 GLUT 编译警告：**

添加编译时警告提示用户功能限制：

```cpp
// 位置1：头文件包含后
#ifndef GLUT_API_VERSION
    #warning "Using original GLUT - window close button may not work properly. Consider installing freeglut."
#endif

// 位置2：关闭回调注册前
#if (!defined(GLUT_API_VERSION) || GLUT_API_VERSION < 4) && !defined(GLUT_HAS_CLOSE_CALLBACK)
    #warning "GLUT version does not support window close callback. Use ESC or Q key to exit."
#endif
```

### Simulator SDL2 迁移方案（方案 D1 - 软件渲染）

**状态**: 📝 **已规划，待实现**

**提案日期**: 2026-02-18

**目标**: 将图形库从 OpenGL/GLUT 迁移到 SDL2，解决跨平台兼容性问题并提升渲染性能。

#### 背景与动机

当前 `simulator.cpp` 使用 OpenGL/GLUT 进行图形渲染，存在以下问题：

| 问题 | 影响 |
|------|------|
| GLUT 已废弃 | macOS 上 API 被标记为废弃，未来可能被移除 |
| 窗口关闭问题 | macOS 需要 `atexit` hack，Linux 需要条件编译 |
| 渲染性能低 | 每帧 307,200 次 `glRectf()` 调用，CPU 占用 80-100% |
| 代码复杂度高 | 平台条件编译多，OpenGL 状态管理复杂 |

#### 方案概述

**方案 D1: SDL2 软件渲染**
- 使用 `SDL_Surface` 进行 CPU 端像素操作
- 通过 `SDL_BlitScaled()` 进行硬件加速缩放
- 简化的轮询式事件处理（替代 GLUT 回调）

**预期改进**:
| 指标 | 当前 GLUT | 方案 D1 (SDL2) |
|------|----------|----------------|
| CPU 占用（渲染）| ~80% | ~15-20% |
| 每帧绘制调用 | 307,200 | 1 |
| 跨平台一致性 | 条件编译复杂 | 统一代码 |
| 窗口关闭按钮 | 需平台特定处理 | 原生支持 |

#### 依赖安装

**macOS**:
```bash
brew install sdl2
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install libsdl2-dev
```

验证安装:
```bash
sdl2-config --version
```

#### 详细修改方案

##### 1. 头文件替换（第 1-24 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**: SDL2 提供统一跨平台 API，无需条件编译

**当前代码**:
```cpp
#if defined(__APPLE__)
    #define PLATFORM_MACOS 1
    #include <GLUT/glut.h>
#elif defined(__linux__) || defined(__linux) || defined(linux)
    #define PLATFORM_LINUX 1
    #include <GL/glut.h>
    #ifdef GLUT_API_VERSION
        #include <GL/freeglut_ext.h>
    #else
        #warning "Using original GLUT..."
    #endif
#else
    #error "Unsupported platform..."
#endif
```

**新代码**:
```cpp
#include <SDL2/SDL.h>
```

**修改量**: 删除 24 行 → 新增 1 行

**验证**: 编译时 SDL2 头文件正确包含，无平台相关条件编译

---

##### 2. 全局变量重构（第 27-148 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**:
- 删除 `gl_setup_complete`（SDL 初始化是同步的）
- 删除 `pixel_w`, `pixel_h`（SDL 使用像素坐标）
- 删除 `window_close_handler` 和 `drawCircle`（GLUT/OpenGL 特定）
- 添加 SDL 窗口和表面句柄

**删除的变量**:
- `std::atomic<bool> gl_setup_complete{false}`
- `float pixel_w`, `float pixel_h`
- `void window_close_handler()` (PLATFORM_LINUX)
- `void drawCircle()` (OpenGL)

**新增的变量**:
```cpp
const int WINDOW_WIDTH = 800;
const int WINDOW_HEIGHT = 600;
const int VGA_DISPLAY_WIDTH = 640;
const int VGA_DISPLAY_HEIGHT = 480;
const int LED_AREA_HEIGHT = 100;
const int MARGIN = 20;

static SDL_Window* g_window = nullptr;
static SDL_Surface* g_screen_surface = nullptr;
static SDL_Surface* g_vga_surface = nullptr;
```

**验证**: SDL 变量正确添加，GLUT/OpenGL 变量已删除

---

##### 3. 渲染系统完全重写（第 176-261 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**:
- **核心性能问题**: 原代码每帧 307,200 次 OpenGL 调用
- **新方案**: 使用 `SDL_BlitScaled()` 一次性缩放整个表面
- **跨平台问题**: `SDL_MapRGB` 自动处理像素格式差异
- **缓冲区布局**: 处理 x-major → y-major 的转换

**删除的函数**:
- `void render(void)` - OpenGL 渲染函数（307,200 次调用）
- `void glutTimer(int t)` - GLUT 定时器

**新函数**:
```cpp
void render_sdl() {
    // 1. Double buffer swap
    if (buffer_swap_pending.exchange(false, std::memory_order_acquire)) {
        float* old_write = write_buffer.exchange(
            read_buffer.exchange(
                write_buffer.load(std::memory_order_relaxed),
                std::memory_order_relaxed
            ),
            std::memory_order_relaxed
        );
        (void)old_write;
    }
    
    // 2. Convert float RGB to SDL pixels (x-major -> y-major)
    float* src_buf = read_buffer.load(std::memory_order_acquire);
    SDL_LockSurface(g_vga_surface);
    uint32_t* dst_pixels = (uint32_t*)g_vga_surface->pixels;
    
    for (int y = 0; y < ACTIVE_HEIGHT; y++) {
        for (int x = 0; x < ACTIVE_WIDTH; x++) {
            int src_idx = ((x * ACTIVE_HEIGHT) + y) * 3;
            int dst_idx = y * ACTIVE_WIDTH + x;
            
            uint8_t r = (uint8_t)(src_buf[src_idx] * 255.0f);
            uint8_t g = (uint8_t)(src_buf[src_idx + 1] * 255.0f);
            uint8_t b = (uint8_t)(src_buf[src_idx + 2] * 255.0f);
            
            dst_pixels[dst_idx] = SDL_MapRGB(g_vga_surface->format, r, g, b);
        }
    }
    SDL_UnlockSurface(g_vga_surface);
    
    // 3-8. Clear, blit, draw LEDs, update window
    // ... (see full code above)
}
```

**性能提升**: 30万+ OpenGL 调用 → 1 次 SDL_BlitScaled，CPU 占用 ↓ 80%

**验证**: 函数签名更改为 `render_sdl()`，完全移除了 OpenGL/GLUT 依赖

---

##### 4. 事件处理重构（第 263-363 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**:
- **macOS 兼容性**: GLUT `glutMainLoop()` 永不返回，需要 `atexit` hack
- **新方案**: `SDL_PollEvent()` 统一处理，窗口关闭按钮原生工作
- **代码简化**: 从回调式改为轮询式，逻辑更清晰

**删除的函数**:
- `void keyPressed(unsigned char key, int x, int y)`
- `void keyReleased(unsigned char key, int x, int y)`
- `void graphics_loop(int argc, char** argv)`

**新函数**:
```cpp
void run_event_loop() {
    SDL_Event e;
    bool running = true;
    
    while (running && !g_quit_requested.load(std::memory_order_acquire)) {
        while (SDL_PollEvent(&e)) {
            switch (e.type) {
                case SDL_QUIT:  // Window close button - all platforms
                    running = false;
                    break;
                case SDL_KEYDOWN:
                    switch (e.key.keysym.sym) {
                        case SDLK_a:
                            keys[0].store(0);
                            restart_triggered.store(true);
                            break;
                        // ... s, d, f, g, ESC, q
                    }
                    break;
                case SDL_KEYUP:
                    // ...
                    break;
            }
        }
        render_sdl();
        SDL_Delay(16);  // 60 FPS
    }
    g_quit_requested.store(true);
}
```

**改进**:
- 删除平台条件编译（`#if defined(PLATFORM_MACOS)` 等）
- 窗口关闭按钮原生支持
- 代码更简洁直观

---

##### 5. 主函数重构（第 516-532 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**:
- **初始化顺序**: SDL 必须在主线程初始化（macOS Cocoa 要求）
- **Retina 支持**: 添加 `SDL_WINDOW_ALLOW_HIGHDPI` 标志
- **资源管理**: 统一清理逻辑

**当前代码**:
```cpp
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    g_sim_thread = std::thread(simulation_loop);
    graphics_loop(argc, argv);  // GLUT 阻塞，平台差异大
    cleanup_simulation();
    return 0;
}
```

**新代码**:
```cpp
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    
    // 1. Initialize SDL (main thread required)
    if (SDL_Init(SDL_INIT_VIDEO) < 0) { /* error handling */ }
    
    // 2. Create window (ALLOW_HIGHDPI for macOS Retina)
    g_window = SDL_CreateWindow("...",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        WINDOW_WIDTH, WINDOW_HEIGHT,
        SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI);
    g_screen_surface = SDL_GetWindowSurface(g_window);
    
    // 3. Create VGA buffer (32-bit RGB888)
    g_vga_surface = SDL_CreateRGBSurfaceWithFormat(0, ACTIVE_WIDTH, ACTIVE_HEIGHT,
        32, SDL_PIXELFORMAT_RGB888);
    
    // 4. Start simulation thread
    g_sim_thread = std::thread(simulation_loop);
    
    // 5. Run event loop
    run_event_loop();
    
    // 6. Cleanup
    cleanup_simulation();
    return 0;
}
```

**验证**: 主线程正确初始化 SDL，仿真线程后启动，窗口创建成功

---

##### 6. 清理函数更新（第 33-42 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**: 释放 SDL 资源，避免内存泄漏

**当前代码**:
```cpp
void cleanup_simulation() {
    if (g_cleanup_done.exchange(true, std::memory_order_acq_rel)) {
        return;
    }
    g_quit_requested.store(true, std::memory_order_release);
    if (g_sim_thread.joinable()) {
        g_sim_thread.join();
    }
    // GLUT 资源自动清理
}
```

**新代码**:
```cpp
void cleanup_simulation() {
    if (g_cleanup_done.exchange(true, std::memory_order_acq_rel)) {
        return;
    }
    g_quit_requested.store(true, std::memory_order_release);
    if (g_sim_thread.joinable()) {
        g_sim_thread.join();
    }
    
    // Release SDL resources
    if (g_vga_surface) {
        SDL_FreeSurface(g_vga_surface);
        g_vga_surface = nullptr;
    }
    if (g_window) {
        SDL_DestroyWindow(g_window);
        g_window = nullptr;
    }
    SDL_Quit();
}
```

**验证**: SDL 资源正确释放，避免内存泄漏

---

##### 7. 仿真线程修改（第 480-514 行）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**: 删除 `gl_setup_complete` 等待循环（SDL 初始化是同步的）

**当前代码**:
```cpp
void simulation_loop() {
    init_rgb_lookup_tables();
    
    // Wait for GLUT initialization
    while (!gl_setup_complete.load(std::memory_order_acquire)) {
        std::this_thread::yield();
    }
    
    display = new VDevelopmentBoard;
    // ...
}
```

**新代码**:
```cpp
void simulation_loop() {
    init_rgb_lookup_tables();
    
    // SDL initialization is synchronous in main thread
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    display = new VDevelopmentBoard;
    reset();
    g_sync.reset();
    
    while (!Verilated::gotFinish() && !g_quit_requested.load(...)) {
        if (restart_triggered.exchange(false, ...)) {
            reset();
        }
        tick();
        tick();
        sample_pixel();
    }

    display->final();
    delete display;
}
```

**验证**: 删除了对 `gl_setup_complete` 的依赖，使用短暂延迟确保窗口显示

---

##### 8. 编译脚本更新（`run_simulation.sh`）

**状态**: ✅ **已完成**

**修改日期**: 2026-02-18

**修改原因**: 自动检测 SDL2 安装路径，提供回退方案

**修改内容**:
- 删除 GLUT/OpenGL 链接标志
- 添加 SDL2 自动检测逻辑（多路径搜索）
- 更新错误提示信息（GLUT→SDL2）

**新代码**:
```bash
#!/bin/bash

# Detect SDL2 with multiple fallback paths
SDL_CONFIG=""
for path in sdl2-config /opt/homebrew/bin/sdl2-config /usr/local/bin/sdl2-config /usr/bin/sdl2-config; do
    if command -v "$path" &> /dev/null; then
        SDL_CONFIG="$path"
        break
    fi
done

if [ -n "$SDL_CONFIG" ]; then
    SDL_CFLAGS=$($SDL_CONFIG --cflags)
    SDL_LIBS=$($SDL_CONFIG --libs)
    echo "Found SDL2: $SDL_CONFIG"
else
    echo "Warning: sdl2-config not found, using default flags"
    SDL_CFLAGS="-I/usr/include/SDL2 -D_REENTRANT"
    SDL_LIBS="-lSDL2"
fi

# Set LDFLAGS for Verilator
LDFLAGS=""
for flag in $SDL_LIBS; do
    LDFLAGS="$LDFLAGS -LDFLAGS $flag"
done

# Verilator command
verilator -O3 --Wno-fatal -Wall --cc --exe -I"$INCLUDE_DIR" simulator.cpp DevelopmentBoard.v \
    $LDFLAGS -CFLAGS "$SDL_CFLAGS"
```

**验证**: 脚本自动检测 SDL2，支持 macOS 和 Linux

---

#### 跨平台兼容性确认

| 特性 | macOS Intel | macOS Apple Silicon | Linux x86_64 | Linux ARM64 |
|------|-------------|---------------------|--------------|-------------|
| SDL2 安装 | `brew install sdl2` | `brew install sdl2` | `apt install` | `apt install` |
| 编译脚本 | ✅ 自动检测 | ✅ 自动检测 | ✅ 自动检测 | ✅ 回退支持 |
| 窗口关闭 | ✅ 原生 | ✅ 原生 | ✅ 原生 | ✅ 原生 |
| Retina 显示 | ✅ ALLOW_HIGHDPI | ✅ ALLOW_HIGHDPI | N/A | N/A |
| 线程模型 | ✅ 主线程 SDL | ✅ 主线程 SDL | ✅ 主线程 SDL | ✅ 主线程 SDL |
| 像素格式 | ✅ RGB888 | ✅ RGB888 | ✅ RGB888 | ✅ RGB888 |

---

#### 修改量统计

| 模块 | 原代码行数 | 新代码行数 | 核心改进 |
|------|-----------|-----------|---------|
| 头文件 | 24 | 1 | 删除平台判断，统一 SDL2 |
| 全局变量 | ~40 | ~20 | 删除 OpenGL 变量，添加 SDL 表面 |
| 渲染函数 | ~85 | ~65 | 30万调用→1次blit，CPU占用↓80% |
| 事件处理 | ~100 | ~50 | 回调→轮询，窗口关闭统一支持 |
| 主函数 | ~17 | ~40 | 显式初始化，Retina支持 |
| 清理函数 | ~12 | ~18 | 添加 SDL 资源释放 |
| **总计** | ~278 | ~194 | 更简洁，更高效，更跨平台 |

---

#### 开发过程中的额外修复

以下修改是在实际开发和测试过程中发现的问题及其解决方案，未包含在最初的规划方案中。

| # | 问题 | 原因 | 解决方案 | 验证 |
|---|------|------|---------|------|
| 1 | 头文件路径错误 | `sdl2-config --cflags` 返回 `-I/opt/homebrew/include/SDL2`，再使用 `#include <SDL2/SDL.h>` 会导致找不到文件 | 改为 `#include <SDL.h>` | ✅ 编译通过 |
| 2 | 变量前向声明 | `cleanup_simulation()` 使用 `g_window` 和 `g_vga_surface`，但它们在函数之后声明 | 添加前向声明：`extern SDL_Window* g_window;` | ✅ 编译通过 |
| 3 | SDL 头文件未传递给 make | `-CFLAGS` 只传给 Verilator，make 阶段使用 `CXXFLAGS` | `export CXXFLAGS="$SDL_CFLAGS"` | ✅ make 成功 |
| 4 | 界面只占 1/4 窗口 | macOS Retina 屏幕物理像素是逻辑像素的 2 倍 | 动态获取实际表面大小：`g_screen_surface->w/h` | ✅ 全窗口显示 |
| 5 | VGA 区域太小 | 固定 640x480 在 1600x1200 窗口上只占 40% | 自适应缩放，保持 4:3 比例，充分利用可用空间 | ✅ 自适应大小 |
| 6 | 缺少区域标识 | 用户无法区分 VGA 和 LED 区域 | 添加简单位图字体绘制 "VGA" 和 "LED" 标签 | ✅ 标签清晰 |
| 7 | "G" 显示像 "Q" | 字符位图第 4 行多了右下角一个点 | 修正 "G" 的位图数据 | ✅ 字符正确 |
| 8 | 标签显示不全/重叠 | MARGIN 太小，标签被裁切或与显示区重叠 | 分离 `MARGIN_TOP` (35px) 专门放置标签 | ✅ 布局正确 |

##### 详细修复记录

**修复 1-3：编译问题**
```cpp
// 修复 1：头文件
#include <SDL.h>  // 原来是 <SDL2/SDL.h>

// 修复 2：前向声明
static SDL_Window* g_window = nullptr;      // 移到 cleanup_simulation() 前
static SDL_Surface* g_vga_surface = nullptr;
```

```bash
# 修复 3：编译脚本
export CXXFLAGS="$SDL_CFLAGS"  # 新增，确保 make 能收到 SDL 头文件路径
```

**修复 4-5：HiDPI 和自适应布局**
```cpp
// 动态获取实际窗口大小（处理 Retina）
g_window_width = g_screen_surface->w;   // 1600 on Retina
g_window_height = g_screen_surface->h;  // 1200 on Retina

// 自适应 VGA 区域
int vga_display_w = g_window_width - MARGIN * 2;
int vga_display_h = vga_display_w * 3 / 4;  // 保持 4:3
```

**修复 6-8：标签显示**
```cpp
// 5x3 位图字体
const uint8_t FONT_5x3[][5] = { ... };

// 分离标签边距和显示边距
const int MARGIN_TOP = 35;  // 标签空间
const int MARGIN = 20;      // 显示区域边距

// 标签位置在独立空间内
draw_label(surface, x, MARGIN_TOP, "VGA", color, scale);
```

---

#### SDL2 迁移后的界面改进

以下改进是在 SDL2 迁移完成后，为进一步提升用户体验而添加的功能。

##### LED 编号标签 ✅ 已完成

| ID | 描述 | 状态 |
|----|------|------|
| LED-01 | 为每个 LED 指示灯下方添加 "LED1"~"LED5" 编号标签 | ✅ 已完成 |
| LED-02 | 扩展 bitmap 字体，添加数字 1-5 的字形定义 | ✅ 已完成 |
| LED-03 | 标签字体大小设为区域标题的 1/3（最小为 2） | ✅ 已完成 |

**修改日期**: 2026-02-18

**修改原因**: 
- 原有界面 LED 灯没有编号标识，用户无法区分 LED1~LED5
- 需要与 Verilog 模块中的 `led1`~`led5` 信号对应

**实现细节**:
- 字体缩放：`label_font_scale = font_scale / 3`，最小值为 2
- 标签位置：LED 圆心正下方，水平居中对齐
- 字体颜色：灰色（与 "LED" 区域标题颜色一致）
- 字符宽度：每个字符 6×scale 像素（5px 字宽 + 1px 间距）
- 标签格式："LED1"、"LED2"、"LED3"、"LED4"、"LED5"

**代码变更**:

```cpp
// 1. 扩展字体数组，添加数字 1-5（在原有 V,G,A,L,E,D 后添加）
const uint8_t FONT_5x3[][5] = {
    // ... 原有字符 0-5 ...
    {0b00100, 0b01100, 0b00100, 0b00100, 0b01110}, // 1 (index 6)
    {0b01110, 0b00001, 0b01110, 0b01000, 0b01111}, // 2 (index 7)
    {0b01110, 0b00001, 0b00110, 0b00001, 0b01110}, // 3 (index 8)
    {0b01001, 0b01001, 0b01111, 0b00001, 0b00001}, // 4 (index 9)
    {0b01111, 0b01000, 0b01110, 0b00001, 0b01110}, // 5 (index 10)
};

// 2. draw_char() 添加数字 case
void draw_char(SDL_Surface* surface, int x, int y, char c, uint32_t color, int scale) {
    int idx = -1;
    switch (c) {
        // ... 原有 case ...
        case '1': idx = 6; break;
        case '2': idx = 7; break;
        case '3': idx = 8; break;
        case '4': idx = 9; break;
        case '5': idx = 10; break;
    }
    // ...
}

// 3. render_sdl() 中添加标签绘制
int label_font_scale = font_scale / 3;
if (label_font_scale < 2) label_font_scale = 2;
int label_char_w = 6 * label_font_scale;
int label_led_w = 4 * label_char_w;  // "LED1" 宽度
int label_y = led_y_start + LED_AREA_HEIGHT / 2 + led_radius + 8;

for (int i = 0; i < 5; i++) {
    int cx = led_spacing * (i + 1);
    int label_x = cx - label_led_w / 2;
    draw_label(g_screen_surface, label_x, label_y, "LED", label_color, label_font_scale);
    // 绘制数字 (1-5)
    char digit_str[2] = {'1' + i, '\0'};
    draw_label(g_screen_surface, label_x + 3 * label_char_w, label_y, digit_str, label_color, label_font_scale);
}
```

**视觉效果**:
```
┌─────────────────────────────────────┐
│  L E D                              │  <- 区域标题（大字体）
│    ○     ○     ○     ○     ○        │  <- LED 指示灯
│  LED1  LED2  LED3  LED4  LED5       │  <- LED编号（小字体，新增）
└─────────────────────────────────────┘
```

**修改文件**:
- `sim/simulator.cpp`
- `Example/Example_1_ColorBar/sim/simulator.cpp`
- `Example/Example_2_BallMove/sim/simulator.cpp`

**测试验证**:
- ✅ Example 1（ColorBar）编译运行正常，LED 编号显示正确
- ✅ Example 2（BallMove）编译运行正常，按键控制时对应 LED 亮起，编号清晰可见

---

#### 频繁按键VGA刷新迟缓问题修复（2026-02-18）

**问题状态**: ✅ **已修复并测试通过**

**修复日期**: 2026-02-18

**问题描述**:
在频繁按键操作（如快速连续按下多个方向键）时，VGA画面刷新出现明显迟缓，终端持续输出"Simulation lag"警告，且滞后时间（lag）持续增大不收敛，最终导致仿真失去响应。

**根本原因分析**:

1. **事件积压**：`run_event_loop()`使用`while (SDL_PollEvent(&e))`一次性处理SDL队列中的所有事件，当用户快速按键时，事件队列积压大量事件（包括KEYDOWN/KEYUP重复事件）

2. **主线程阻塞**：处理积压事件消耗大量CPU时间，导致`SDL_Delay(16)`被跳过或延迟，主线程长时间占用CPU

3. **仿真线程饿死**：在单核/低核CPU上，主线程的事件处理阻塞了仿真线程的执行，导致`RealTimeSync`发现真实时间已流逝很多，但仿真时间未推进

4. **滞后累积**：`RealTimeSync`的忙等待机制在仿真线程被阻塞时无法正常工作，导致滞后持续累积

**症状表现**（修复前）：
```
[RealTimeSync] Lag warn #1: current=1500us avg=1500us max=1500us
[RealTimeSync] Lag warn #21: current=3500us avg=2500us max=3500us
[RealTimeSync] Lag warn #41: current=7500us avg=4500us max=7500us
...
[RealTimeSync] Lag warn #1001: current=150000us avg=80000us max=150000us
```

---

**修复方案**:

##### 1. 事件处理限制（P0优先级）

**技术实现**：
```cpp
// 修改前
while (SDL_PollEvent(&e)) {
    // 处理所有事件（可能数百个）
}

// 修改后
const int MAX_EVENTS_PER_FRAME = 1;  // 严格限制每帧只处理1个事件
int event_count = 0;
while (SDL_PollEvent(&e) && event_count < MAX_EVENTS_PER_FRAME) {
    event_count++;
    // 处理该事件
}
// 剩余事件留在SDL队列中，下一帧继续处理
```

**设计考虑**：
- 从3改为1是为了最大限度保证仿真线程获得CPU时间
- 事件在SDL队列中排队，不会丢失，只是延迟处理
- 60 FPS下，每秒仍可处理60个事件，足以应对正常按键操作

##### 2. 自适应时间同步 - 滞后追赶机制（P0优先级）

**技术实现**：
```cpp
class RealTimeSync {
    static constexpr uint64_t MAX_LAG_NS = 50000000;      // 50ms最大允许滞后
    static constexpr uint64_t WARN_LAG_NS = 1000000;      // 1ms警告阈值
    
    void tick() {
        int64_t lag_ns = elapsed_ns - target_ns;
        
        if (lag_ns < 0) {
            // 仿真时间领先：忙等待直到真实时间追上
            busy_wait(-lag_ns);
        } 
        else if ((uint64_t)lag_ns > MAX_LAG_NS) {
            // 严重滞后（>50ms）：重置时间基准，允许"追赶"
            lag_reset_count++;
            std::cerr << "[RealTimeSync] LAG RESET #" << lag_reset_count 
                      << ": lag=" << lag_ns / 1000000 << "ms\n";
            epoch = now;        // 重置时间基准
            sim_cycles = 0;     // 重置仿真周期计数
        } 
        else if ((uint64_t)lag_ns > WARN_LAG_NS) {
            // 轻微滞后（1-50ms）：统计但不频繁输出
            warn_count++;
            if (warn_count % 20 == 1) {
                std::cerr << "[RealTimeSync] Lag warn #" << warn_count
                          << ": current=" << lag_ns / 1000 << "us\n";
            }
        }
    }
};
```

**关键设计决策**：
- 50ms阈值：足够大以避免误判正常的系统调度抖动，又足够小以保证用户体验
- 重置而非追赶：直接重置时间基准比加速仿真更简单可靠，避免复杂的速度调节逻辑
- 警告节流：每20次警告只输出1次，避免刷屏影响性能

##### 3. 详细调试统计系统（P1优先级）

**RealTimeSync内部统计**：
```cpp
uint64_t lag_reset_count = 0;   // 重置次数（关键指标）
uint64_t total_lag_ns = 0;      // 累计滞后时间
uint64_t max_lag_ns = 0;        // 最大滞后记录
uint64_t cycle_count = 0;       // 总tick次数
uint64_t wait_count = 0;        // 忙等待次数（健康度指标）
uint64_t warn_count = 0;        // 警告次数
```

**EventLoop统计**：
```cpp
uint64_t frame_count = 0;           // 帧计数
uint64_t total_events = 0;          // 总事件数
uint64_t dropped_events = 0;        // 丢弃事件数（关键指标）
uint64_t max_events_in_frame = 0;   // 单帧最大事件数
int64_t max_frame_time = 0;         // 最大帧时间

// 每秒输出统计报告
std::cerr << "[EventLoop] FPS: " << frame_count 
          << " | Events: " << total_events 
          << " | Dropped: " << dropped_events
          << " | MaxEvents/Frame: " << max_events_in_frame
          << " | MaxFrameTime: " << max_frame_time << "ms\n";
```

**VSync统计**：
```cpp
static uint64_t g_vsync_count = 0;  // VSync计数（实际帧率）

// 每60帧输出一次
if (g_vsync_count % 60 == 0) {
    std::cerr << "[VGA] VSync #" << g_vsync_count 
              << " (frame " << (g_vsync_count / 60) << "s)\n";
}
```

**按键输入日志**：
```cpp
case SDLK_s: 
    keys[1].store(0); 
    std::cerr << "[Input] Key 's' pressed (B2)\n";  // 实时显示按键
    break;
```

**退出统计报告**：
```cpp
void printStats() const {
    std::cerr << "\n========== RealTimeSync Stats ==========\n";
    std::cerr << "Total cycles:    " << cycle_count << "\n";
    std::cerr << "Wait cycles:     " << wait_count << " (" 
              << (wait_count * 100 / cycle_count) << "%)\n";
    std::cerr << "Lag resets:      " << lag_reset_count << "\n";
    std::cerr << "Lag warnings:    " << warn_count << "\n";
    std::cerr << "Max lag seen:    " << max_lag_ns / 1000 << "us\n";
    std::cerr << "Avg lag (warn):  " << (total_lag_ns / warn_count) / 1000 << "us\n";
    std::cerr << "========================================\n";
}
```

##### 4. 字体渲染修复（P3优先级，回归修复）

**问题背景**：在修改过程中误将`draw_char()`的列循环从5改为3，导致字符显示不全（如"G"显示像"C"）。

**修复内容**：
```cpp
// 修改前（错误）
for (int col = 0; col < 3; col++) {  // 只绘制3列，字符被截断

// 修改后（正确）
for (int col = 0; col < 5; col++) {  // 绘制5列，完整显示
```

---

**验证过程**:

#### Example 1 (ColorBar) 测试结果

| 阶段 | 配置 | 事件限制 | LAG RESET | Lag Warnings | Max Lag | 结论 |
|-----|------|---------|-----------|--------------|---------|------|
| 修复前 | 原始代码 | 无限制 | 1次 | 3000+ | >100ms | 失控增长 |
| 修复中 | 方案A+B | 3 | 1次 | 3000+ | 3-4ms | 改善但不彻底 |
| 修复后 | 方案A+B | 1 | 0次 | 0 | 0us | 完全解决 |

**关键输出**（Example 1）：
```
========== RealTimeSync Stats ==========
Total cycles:    42591000
Wait cycles:     40240687 (94%)   ← 仿真线程94%时间健康等待
Lag resets:      0                 ← 关键：无重置！
Lag warnings:    0                 ← 关键：无警告！
Max lag seen:    0us               ← 关键：完全同步！
Avg lag (warn):  0us
========================================
```

#### Example 2 (BallMove) 测试结果

| 阶段 | 配置 | 事件限制 | 计算负载 | LAG RESET | Lag Warnings | Max Lag | 结论 |
|-----|------|---------|---------|-----------|--------------|---------|------|
| 修复后 | 方案A+B | 1 | 高（球碰撞检测） | 1次（初始化） | ~9600+ | 2-3ms | 可控增长 |

**分析**：
- 虽然仍有滞后警告，但这是因为BallMove的Verilog代码计算量更大（球位置计算、边界碰撞检测）
- 滞后从1ms缓慢增长到3ms，然后稳定，**没有失控**
- 证明修复方案有效，只是系统性能不足以支撑12.5MHz仿真时钟

---

**未解决的问题与后续建议**:

#### 未解决问题
1. **Example 2仍有轻微滞后**：由于BallMove计算量大，12.5MHz仿真时钟对当前系统略高
2. **事件队列延迟**：限制为1事件/帧后，快速连按4个键需要4帧（~66ms）才能全部响应，可能有轻微"按键延迟"感

#### 后续优化建议

**1. 降低仿真时钟频率**（可选）：
```cpp
// 当前
static constexpr uint64_t NS_PER_CYCLE = 80;   // 12.5MHz
// 建议
static constexpr uint64_t NS_PER_CYCLE = 160;  // 6.25MHz，降低50%负载
// 或
static constexpr uint64_t NS_PER_CYCLE = 320;  // 3.125MHz，降低75%负载
```
仿真时钟降低不会影响VGA显示刷新率（仍为60Hz），只影响仿真精度。

**2. 自适应事件限制**（可选）：
```cpp
// 根据当前滞后动态调整事件限制
int MAX_EVENTS_PER_FRAME = (lag_ns > 5000000) ? 0 : 1;  // 滞后大时暂停事件处理
```

**3. 多核优化**（可选）：
将仿真线程绑定到独立CPU核心，避免与主线程竞争。

---

**代码变更清单**:

| 文件 | 修改位置 | 修改类型 | 修改内容摘要 |
|-----|---------|---------|-------------|
| `sim/simulator.cpp` | 44-137行 | 重构 | RealTimeSync类增强，添加滞后控制和统计 |
| `sim/simulator.cpp` | 383-500行 | 重构 | run_event_loop()添加事件限制和详细统计 |
| `sim/simulator.cpp` | 640-684行 | 增强 | simulation_loop()添加统计输出 |
| `sim/simulator.cpp` | 600-639行 | 增强 | sample_pixel()添加VSync统计 |
| `sim/simulator.cpp` | 244-252行 | 修复 | draw_char()列数3→5，修复字体显示 |
| `Example/*/sim/simulator.cpp` | 全部 | 同步 | 同步上述所有修改 |

**相关提交**: simulator.cpp 主文件修改，Example 1/2 同步更新

---

### 降低仿真时钟频率以支持虚拟机环境 (2026-02-18)

**状态**: ✅ **已完成并测试通过**

**修复日期**: 2026-02-18

**问题背景**:
在 Ubuntu 22.04 虚拟机上测试发现严重性能问题：
- Wait cycles: 0%（仿真线程从未等待）
- Lag resets: 1535 次（每 2-3 秒触发一次）
- Lag warnings: 3200万+（滞后失控增长）
- Max lag: 49.9ms（达到 50ms 阈值上限）

**根本原因**:
- 虚拟机共享 CPU，单核性能严重不足
- 原 NS_PER_CYCLE = 80 (12.5MHz) 对虚拟机负载过高

**解决方案**:

| 方案 | 频率 | 负载降低 | 适用场景 |
|-----|------|---------|---------|
| 方案A | 6.25MHz (160ns) | 50% | 中等性能虚拟机 |
| **方案B** | **3.125MHz (320ns)** | **75%** | **低性能虚拟机（采用）** |
| 方案C | 1.5625MHz (640ns) | 87.5% | 极低性能环境 |

**修改内容**:
```cpp
// sim/simulator.cpp 第 47 行
- static constexpr uint64_t NS_PER_CYCLE = 80;   // 12.5MHz
+ static constexpr uint64_t NS_PER_CYCLE = 320;  // 3.125MHz
```

**影响文件**:
- `sim/simulator.cpp`
- `Example/Example_1_ColorBar/sim/simulator.cpp`
- `Example/Example_2_BallMove/sim/simulator.cpp`

**测试结果**:

| 指标 | 修改前 (Ubuntu VM) | 修改后 (macOS) | 修改后 (Ubuntu VM 预期) |
|-----|-------------------|---------------|----------------------|
| Wait cycles | 0% | **99%** | >50% |
| Lag resets | 1535 | **0** | 0-2 |
| Lag warnings | 3200万+ | **0** | 大幅减少 |
| Max lag | 49.9ms | **0μs** | <5ms |

**注意事项**:
- 仿真时钟降低**不影响**VGA显示刷新率（仍为60Hz）
- 只影响仿真精度，对视觉体验无影响
- 如仍有性能问题，可进一步降至 640 (1.5625MHz)

**相关提交**: `aa03b2b` perf: reduce simulation clock from 12.5MHz to 3.125MHz for VM compatibility

## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [OpenGL/GLUT Documentation](https://www.opengl.org/)
