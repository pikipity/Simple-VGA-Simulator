# Simple VGA Simulator v2

**EIE330 · 虚拟 FPGA 开发板实验台 / Virtual FPGA Development Board Lab Bench**

在浏览器里完整走一遍 FPGA 开发流程：写 Verilog → 写 QSF 引脚约束 → Analysis & Synthesis → Fitter (Place & Route) → Assembler → Programmer（USB-Blaster 烧录）→ 上电 → 按按键看现象。不需要真实的开发板，也不需要虚拟机。

Run the full FPGA workflow in your browser — Verilog → QSF → synthesis → place & route → programming files → USB-Blaster programming → power on → press buttons. No physical board, no virtual machine.

![虚拟开发板运行中 / Development board running](SchematicDiagram/v2_board_running.png)

## v2 是什么 / What v2 Is

v2 是两个独立的浏览器页面：

| 页面 / Page | 是什么 / What it is |
|-------------|---------------------|
| **EDA Tool** | 仿 Quartus Prime 的开发工具：工程、Tasks 编译流程（Analysis & Synthesis / Fitter / Assembler）、Pin Planner、时序报告、Programmer |
| **Development Board** | 仿真实物布局的虚拟开发板：Cyclone IV E EP4CE10F17C8N、Y7 50MHz 晶振、SW1~SW5 按键、LED2~LED5 蓝色 LED、VGA 外接显示器、电源开关 |

面向开发者 / For developers：Python 标准库后端（零第三方依赖）+ 无构建原生前端，编译与仿真由 Verilator + Yosys 工具链驱动；无 SDL2、无 make、无虚拟机。

## 你需要装什么 / The Only Thing You Install

| 平台 / Platform | 安装命令 / Install command |
|-----------------|---------------------------|
| Ubuntu / Debian | `sudo apt install verilator yosys g++` |
| macOS | `brew install verilator yosys`（编译器来自 Xcode CLT：`xcode-select --install`） |
| Windows | MSYS2 中 `pacman -S mingw-w64-x86_64-verilator mingw-w64-x86_64-gcc mingw-w64-x86_64-yosys`，并把 `C:\msys64\mingw64\bin`（按实际安装路径调整）加入 PATH |

版本要求 / Required versions：Verilator ≥ 4.0，Yosys ≥ 0.9，g++ ≥ 7。
验证 / Verify：`verilator --version`、`yosys --version`、`g++ --version`。

**不再需要** / No longer needed：虚拟机、WSL、SDL2、make、Flutter、Qt。

## 三步上手 / Quick Start

1. **获取 / Get it** — GitHub Releases 下载对应平台的压缩包并解压（或源码运行 `python main.py`，Python ≥ 3.9，零第三方依赖）
2. **启动 / Launch** — 双击启动，浏览器自动打开 EDA Tool 页
3. **跑通示例 / Run an example** — Open Project… 选择 `Example/Example_1_ColorBar` → 双击 Tasks 里的 Compile Design ▶ → 切到 Development Board 页拨 POWER 开关上电 → 回 EDA Tool 页打开 Programmer 点 Start → 回到板子页看彩条

## 示例工程 / Example Projects

| 示例 / Example | 内容 / Content |
|----------------|----------------|
| `Example/Example_1_ColorBar` | 640×480 彩色条纹，无按键交互，用来熟悉完整流程 |
| `Example/Example_2_BallMove` | 紫色背景上的蓝色小球；按 SW2~SW5（KEY1~KEY4）移动小球，按住时对应 LED2~LED5 点亮 |

## 文档 / Documentation

- **[学生手册（中英双语）](Manual%20for%20EIE330%20Students.md)** — 完整安装、开发板说明、QSF 参考、示例与故障排除

## License

[MIT](LICENSE) © 2025 Ze Wang
