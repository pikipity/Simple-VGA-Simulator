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


## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [OpenGL/GLUT Documentation](https://www.opengl.org/)
