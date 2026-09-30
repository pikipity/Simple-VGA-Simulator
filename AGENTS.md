# Simple VGA Simulator v2 - 虚拟开发板实验台

> **版本说明**：v2 是全面重构（分支 `v2-web-board`）。v1 的 Flutter GUI + SDL2 窗口方案因跨平台失败面过大被废弃（见文末 Change History）。本文档描述 v2 的目标架构，是后续所有开发的设计契约。

## 项目概述

面向 EIE330 课程的**虚拟 FPGA 开发板实验台**。学生在本机浏览器中获得两样东西：

1. 一套仿 Quartus Prime 的 EDA 工具（工程、综合、布线、生成烧录文件、编程器）
2. 一块仿真实物布局的虚拟开发板（Cyclone IV EP4CE10F17C8N 芯片、50MHz 晶振、5 个按键、4 个 LED、VGA 接口外接显示器、电源开关）

学生体验完整真实流程：写 Verilog → 写 QSF 引脚约束 → Analysis & Synthesis → Fitter（时序报告）→ Assembler（生成 .sof）→ Programmer（USB-Blaster 烧录）→ 上电 → 按按键看现象。**学生对底层实现（Verilator/Yosys）完全无感知**，他们认为自己在用真实的 EDA 工具和开发板。

## 核心设计原则（v2 重构背景）

v1 失败根因：分发的是构建产物，但运行时环境不受控——Flutter 桌面壳、Verilator、SDL2、make、g++ 全部由学生自装且状态各异，失败面是各层环境变量的乘积。

v2 的核心原则：**把环境差异降到理论下限**。

1. 渲染交给浏览器（各平台最可靠的运行时）；分发包只含 Python 运行时 + 静态文件 + C++ 源码模板，不链接任何系统 GUI 库
2. 后端零第三方 Python 依赖（仅用标准库）；前端零构建步骤（原生 ES Modules，无 vendored 库）
3. 外部工具（verilator / g++ / yosys）锁版本、学生自装，后端负责三级探测（PATH 探测 → 版本验证 → 功能自检）
4. **无 SDL2、无 GNU Make、无 Flutter**。C++ 编译由后端直接拼 g++ 命令完成
5. 单机锁死：后端只绑 127.0.0.1，随机 token 鉴权

## 教学幻觉设计（关键需求）

### 两个独立页面

EDA 工具与开发板是**两个独立页面**，让学生明确意识到这是两个东西：

- **页面 A「EDA 工具」**：仿 Quartus 界面。顶部工程栏（工程路径、Top Entity、器件 `Cyclone IV E EP4CE10F17C8`）；左侧 Tasks 流程树（Compile Design → Analysis & Synthesis / Fitter (Place & Route) / Assembler，外加 Programmer）；中间为报告区（Flow Summary / 时序报告 / Pin Planner / Programmer）。**Messages 平时不可见**，收进底部状态栏一个带角标的按钮，编译失败时角标变红，学生按需点开
- **页面 B「开发板」**：实物摆拍视角。整页是一块板子 + 一台独立显示器（VGA 线连接）。板面元素见下文「板卡定义」。**首次进入默认断电**

两页状态由后端统一持有，WebSocket 同步。

### 烧录与电源语义（对齐真实 JTAG）

| 操作 | 板子表现 |
|------|---------|
| 板子断电时点 Programmer | 报错"未检测到开发板，请检查电源和 USB-Blaster 连接" |
| 烧录成功 | CONF_DONE 灯亮，设计开始运行 |
| **改代码后重新 Programmer（不断电）** | CONF_DONE 熄灭 → 进度条 → 重新点亮，显示器短暂 No Signal 后**自动运行新程序**。全程不关闭任何页面/窗口 |
| 断电再上电 | **配置丢失**（SRAM 语义）：CONF_DONE 灭，需重新烧录 |
| 已上电未烧录 | 电源灯亮，按键无任何效果（IO 未配置） |
| VGA 时序错误 | 显示器显示 **No Signal**（>500ms 无新帧即判定） |
| 退出软件 | 板子状态不保留，下次打开回到断电空白态 |

### 按键抖动

真板按键带 4.7KΩ 上拉 + 0.1µF 对地电容（硬件消抖），残余抖动为亚毫秒~2ms 级。仿真器**始终注入**该量级的随机抖动（GUI 无开关）——不消抖的设计应当在板子上暴露问题。

## 板卡定义（board/ep4ce10_pro.json）

虚拟板照抄野火 EP4CE10_Pro 教学板（原理图：`Doc-2-Schematic Diagram of Development Board.pdf`）的简化子集。引脚分配来自原理图 Sheet 4/5/10/12，已获课程负责人确认：

| 板卡资源 | 丝印 | 原理图网络 | FPGA 引脚 | 有效电平 |
|---------|------|-----------|-----------|---------|
| 50MHz 有源晶振 | Y7 | FPGA_CLK | E1 | — |
| 按键 SW1 | RESET | RESET | M15 | 按下=0（4.7KΩ 上拉） |
| 按键 SW2 | KEY1 | KEY1 | M2 | 按下=0 |
| 按键 SW3 | KEY2 | KEY2 | M1 | 按下=0 |
| 按键 SW4 | KEY3 | KEY3 | E15 | 按下=0 |
| 按键 SW5 | KEY4 | KEY4 | E16 | 按下=0 |
| 蓝色 LED | LED2 | LED0 | L7 | 0=亮（阳极经 1KΩ 接 3V3） |
| 蓝色 LED | LED3 | LED1 | M6 | 0=亮 |
| 蓝色 LED | LED4 | LED2 | P3 | 0=亮 |
| 蓝色 LED | LED5 | LED3 | N3 | 0=亮 |
| VGA 行同步 | — | VGA_HSYNC | C2 | 高有效 |
| VGA 场同步 | — | VGA_VSYNC | D1 | 高有效 |
| VGA 数据 | — | VGA_D0~D15 | B4,A2,B5,A6,B6,F6,F7,A7,B7,E8,F8,A8,B8,E7,E6,A5 | RGB565：D[15:11]=R, D[10:5]=G, D[4:0]=B |

VGA 规格：640×480 @ 60Hz，时序参数与 v1 相同（H: sync 96 / back 40 / left 8 / active 640 / right 8 / front 8，V: sync 2 / back 25 / top 8 / active 480 / bottom 8 / front 2；有效区起点 (144, 35)，上升沿检测）。

板卡定义文件同时包含前端布局坐标（SVG 元素位置），板子外观由数据驱动。

## 技术架构

```
学生双击 main.py（或 PyInstaller 包）
  └─ Python 标准库 HTTP 服务（127.0.0.1:随机端口 + token + 心跳看门狗）
       ├─ 页面 A：EDA 工具（工程 → Synthesis → Fitter → Assembler → Programmer）
       └─ 页面 B：开发板（电源/按键 → 后端；后端 → LED/显示器帧）
```

### 目录结构

```
Simple-VGA-Simulator/
├── main.py                     # 启动器：起服务、生成 token、打开浏览器
├── config.py                   # 版本、锁定工具版本、路径
├── backend/
│   ├── app.py                  # HTTP 路由 + 静态托管 + token + 看门狗
│   ├── ws.py                   # 最小 WebSocket 服务端实现（RFC6455，标准库）
│   └── services/
│       ├── diagnostics.py      # verilator/g++/yosys 三级探测与版本验证
│       ├── toolchain.py        # 工具链提供者（native / WSL 回退、路径互译、进程回收）
│       ├── project_service.py  # 工程扫描、Verilog ANSI 端口解析
│       ├── qsf_service.py      # QSF 解析/校验/生成（对照 board JSON）
│       ├── build_service.py    # 综合(Yosys)/布线(校验+时序估算)/汇编(verilator+g++)
│       └── board_service.py    # 板卡状态机 + 仿真进程托管 + 帧/事件中继
├── board/
│   └── ep4ce10_pro.json        # 板卡定义（引脚表 + 布局）
├── sim/
│   ├── simulator.cpp           # 无头仿真器（v2 重写，见下）
│   └── DevelopmentBoard.v.tpl  # wrapper 模板（v2 固定端口语义）
├── webui/                      # 纯静态，无构建
│   ├── index.html              # 页面 A：EDA 工具
│   ├── board.html              # 页面 B：开发板
│   ├── js/  css/
├── Example/                    # 示例工程（.v + .qsf，已迁移到新板语义）
│   ├── Example_1_ColorBar/
│   └── Example_2_BallMove/
├── tests/                      # 所有测试文件只能放这里
├── SchematicDiagram/           # 文档图
├── main.spec                   # PyInstaller 打包配置
└── .github/workflows/
    ├── build-dev.yml           # dev 分支：四平台构建 + 无头冒烟，不发布
    └── build-release.yml       # main 分支：四平台构建 + 发布 Release
```

**已删除（相对 v1）**：`gui/`（Flutter）、`sim/run_simulation.sh`、`sim/PinPlanner.py`、全部 SDL2 依赖。

### 学生工程结构

```
MyProject/
├── *.v                         # 学生的 Verilog（仅 .v，ANSI 端口）
└── top.qsf                     # 引脚约束（软件提供模板，Pin Planner 可视化编辑）
```

QSF 支持子集（Quartus 真实语法）：

```tcl
set_global_assignment -name TOP_LEVEL_ENTITY top
set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE10F17C8
set_location_assignment PIN_E1 -to clk
set_location_assignment PIN_M15 -to sys_rst_n
set_location_assignment PIN_B4 -to vga_data[0]
create_clock -period 20.000 [get_ports clk]
```

### DevelopmentBoard.v 的语义升级

v1 中 DevelopmentBoard.v 是手写/自动映射的桥接文件；**v2 中它就是 PCB 走线本身**：后端按 QSF 把"学生顶层端口 → 引脚 → 板卡外设"的连接关系生成 wrapper。固定端口（与 simulator.cpp 约定）：

```verilog
module DevelopmentBoard(
    input  wire        clk,                  // E1, 50MHz
    input  wire        key_reset,            // SW1, M15, 按下=0
    input  wire [3:0]  key,                  // SW2~SW5 = key[0]~key[3], 按下=0
    output wire [3:0]  led,                  // LED2~LED5 = led[0]~led[3], 0=亮
    output wire        vga_hs,               // C2
    output wire        vga_vs,               // D1
    output wire [15:0] vga_d                 // RGB565
);
```

学生不接触此文件。wrapper 由模板 `sim/DevelopmentBoard.v.tpl` + QSF 映射生成。

### 构建管线（后端 build_service）

| 步骤（界面词汇） | 底层实现 | 产出 |
|-----------------|---------|------|
| Analysis & Synthesis | `yosys -p 'read_verilog ...; hierarchy -top <top>; proc; check; stat; ltp'` | Quartus 风格 Flow Summary（LE/寄存器数取自 stat）；latch 推断等真实警告进 Messages |
| Fitter (Place & Route) | QSF 引脚合法性校验（对照 board JSON；clk 不在 E1 则警告非专用时钟脚；vga_d 总线必须 16 位全分配；输出端口未分配→warn）；时序估算（见下） | 引脚分配报告 + TimeQuest 风格时序摘要 |
| Assembler | `verilator -O3 --Wno-fatal --cc --top-module DevelopmentBoard` + **后端直接拼 g++**（无 make）：`g++ -O3 simulator.cpp obj_dir/VDevelopmentBoard*.cpp <verilator_root>/include/verilated.cpp -I...` | `output_files/<top>.sof`（= 仿真可执行文件 + JSON 元数据；**固定名覆盖**。先编到 `<top>.sof.new`，成功后若板子正在运行旧镜像则先卸载（CONF_DONE 灭），再原子替换——绕开 Windows 运行中 exe 锁定，且行为可预期） |

**时序估算**（Fitter 内）：`yosys read_verilog ...; synth -top <top>; ltp`（门级映射后测最长路径，取所有模块报告的最大值），Fmax ≈ 1000/(0.2×级数+1.5) MHz，Slack = 20ns − 估算周期。**与真实 Quartus 一致：时序不收敛只是 Critical Warning（Messages 红色提醒），不阻断后续 Assembler/Programmer**——仿真器是功能模型，时序问题不影响虚拟板运行。该估算是教学参考值，已在两个 Example 上校准（E1≈77MHz，E2≈56MHz）。
| Assembler | `verilator -O3 --Wno-fatal --cc --top-module DevelopmentBoard` + **后端直接拼 g++**（无 make）：`g++ -O3 simulator.cpp obj_dir/VDevelopmentBoard*.cpp <verilator_root>/include/verilated.cpp -I...` | `output_files/<top>.sof`（= 仿真可执行文件 + JSON 元数据；每次编译递增修订号 `top_r3.sof`，绕开 Windows 运行中 exe 锁定） |
| Programmer | 校验板已上电 → 进度仪式（~2s）→ spawn `.sof` 进程（后端直接托管，不经 shell）→ 等 READY 握手 → CONF_DONE | 板子运行新程序；旧进程先杀后起 |

Verilator runtime 路径探测：`verilator -getenv VERILATOR_ROOT` → `$VERILATOR_ROOT/include`（apt 安装为 `/usr/share/verilator/include`）。兼容 Verilator ≥ 4.038（Ubuntu 22.04 源版本）。

### 仿真协议（simulator.cpp ↔ backend，二进制管道）

无头仿真器：仿真主循环 + stdin 读取线程。日志全走 stderr，**stdout 只传二进制帧**。

下行（sim → backend，stdout）：

```
启动后: stderr 打印 "SIM_READY\n"（握手）
帧: [u32 magic=0x31474156 'VGA1'][u32 frame_no][u8 led_bits][u8 flags][u16 reserved]
    [payload 640*480*2 字节 RGB565 小端, y-major]
    — 每个 v_sync 上升沿发一帧；led_bits bit i = led[i] 亮（已解 active-low）
```

上行（backend → sim，stdin）：

```
'B' [u8 button_id 0..4 = SW1..SW5] [u8 state: 0=按下 1=松开]
'Q'            退出
```
（抖动注入恒为开，GUI 无开关；simulator.cpp 里的 'I' 命令是未使用的保留路径）

时序 pacing：仿真按**墙钟 60Hz**  pacing（每发一帧 sleep 到下一个 16.67ms 边界；仿真快则等、慢则尽速）——真实板子就是实时的，且天然限制带宽。

### 后端 ↔ 前端

- `GET /`（EDA 工具页）、`GET /board.html`（开发板页）、静态资源
- `POST /api/...`：工程选择、QSF 读写、compile 各步骤、program、power、input（按键）
- `GET /api/diagnostics`（缓存三级探测）；`POST /api/diagnostics/check`（快速：查找+版本）；`POST /api/diagnostics/selftest`（每个工具实际编译/运行小程序）
- `GET/POST /api/settings/tools`：用户手动指定工具路径（settings.json 持久化在程序目录），留空 = 自动检测；保存时校验文件存在且可执行
- QSF 变更（assign/unassign/save）后后端立即广播最新步骤状态（Tasks 窗格即时变 stale）
- `GET /ws`：WebSocket。下行：VGA 二进制帧（每客户端只发最新帧，积压即丢）、`{type:"board",...}` 状态、`{type:"log",...}` 编译日志、`{type:"step",...}` 流程状态
- 所有 `/api/*` 与 `/ws` 需 `X-Board-Token` 头（或 ws query 参数）；只绑 127.0.0.1；校验 Host 头防 DNS rebinding；看门狗：120s 无活动自动退出
- 板卡状态机：`OFF → ON(unconfigured) → CONFIGURED(running)`；power off = 杀进程 + 清配置；program = 杀旧进程 → 起新进程

## 平台与工具链

| 平台 | 工具链（**版本固定**：verilator 4.038 / g++ 11.4.0 / yosys 0.9） | 说明 |
|------|--------|------|
| Linux | `apt install verilator g++ yosys` | 后端与工具同机同 OS |
| macOS | `brew install verilator yosys`（Xcode CLT 提供 g++） | 同上 |
| Windows | MSYS2：`pacman -S mingw-w64-x86_64-verilator mingw-w64-x86_64-gcc yosys`；**原生缺失时自动回退 WSL** | 后端始终原生运行；工具链提供者优先 native、整套回退 WSL（不按单个工具混用） |

**版本策略**：版本号固定为课程参考环境的版本（见上表）。检测到不同版本不是硬错误——Tools 弹窗亮**黄灯**并提示"可尝试使用，建议运行功能自检"；找不到工具才是红灯。

**工具链提供者**（`backend/services/toolchain.py`）：`detect()` 决定 native/WSL；`wrap_cmd()` 负责命令包装与 `D:\...` ↔ `/mnt/d/...` 路径互译；`sof_argv()` 启动仿真进程（WSL 下经 `wsl -e`）；`reap()` 在 wsl.exe 被杀后用 `pkill -xf` 回收 Linux 侧仿真进程（wsl.exe 死亡不会带走子进程）。WSL 管道二进制安全已实证（无 LF 转换）。用户可在设置页手动指定工具路径（存程序目录 `settings.json`）——任何覆盖存在时强制 native 提供者，留空才自动检测。

**无 SDL2、无 make、无强制 WSL、无显示环境配置**。开发主机若工具只在 WSL 里，Windows 侧 `uv run main.py` 即可全功能运行（自动走 WSL 提供者）。

学生侧总安装量：Python 包（绿色软件）+ 各平台包管理器两三条命令（Windows 装了 MSYS2 则连 WSL 都不需要）。

## 开发工作流程规则

### 修改方案确认规则（⚠️ 重要）

**所有修改，先给出详细方案，用户确定方案后再执行。** 必须先说明：改哪些文件、技术方案和理由、影响和风险、预期结果和验证方式。只有用户明确回复"确认/同意/执行"后才能动手。

### Testing File Organization

所有测试脚本/测试数据/临时文件必须放在 `tests/` 目录中，禁止在生产代码目录创建测试文件。

### Git 提交规范

仅在用户明确要求时执行 `git commit`。提交前先 `git status` / `git diff` 展示变更，确认后再提交。

### Main Branch AGENTS.md 管理规则

**main branch 禁止包含 AGENTS.md**。所有合并到 main 的操作都必须排除 AGENTS.md（merge 后 `git rm AGENTS.md` 再 amend，或 `--no-commit` 手动控制）。验证：`git ls-tree HEAD | grep AGENTS.md`。

### AGENTS.md 更新规则

仅在用户明确要求时更新 AGENTS.md。

### 文件唯一性

`sim/simulator.cpp` 与 `sim/DevelopmentBoard.v.tpl` 全仓库**各只有一份**（v1 的四副本同步规范已随 Example 迁移废除）。Example 工程只含学生视角文件（`.v` + `.qsf`），不含仿真模板。

## 实施分期

| 阶段 | 内容 | 验收标准 |
|------|------|---------|
| 一：地基 | 后端骨架 + 无头仿真器 + 最简网页；Example 跑通 | 浏览器 60fps，按键不丢 |
| 二：开发板页 | SVG 板面、电源状态机、断电丢配置、新引脚语义（4 LED / SW1~5） | 断电全灭、No Signal 正确 |
| 三：EDA 工具页 | Tasks 流程、QSF + Pin Planner、Messages 按钮、Programmer、重烧自动更新 | 完整流程；引脚写错会失败；改代码重烧不重启 |
| 四：打磨 | 抖动注入、Example 迁移、手册与 README 重写 | 教学细节完整 |

## Change History

完整历史见 git log。

| 日期 | 变更 |
|------|------|
| 2026-02-17 ~ 2026-06-03 | v1：GLUT→SDL2 迁移、鼠标虚拟按钮、Flutter GUI Launcher、Windows 支持（详见 git log 与 v1 文档） |
| 2026-09-29 | **v2 重构启动**（分支 `v2-web-board`）：废弃 Flutter GUI + SDL2 窗口，改为纯 Web（Python 标准库后端 + 浏览器渲染）；无头仿真器经管道输出帧；仿 Quartus 流程（QSF 约束/Synthesis/Fitter/Assembler/Programmer）；开发板实物化界面（电源开关、断电丢配置、CONF_DONE、No Signal）；引脚表照抄野火 EP4CE10_Pro 原理图；仿真按墙钟 60Hz pacing；按键抖动注入 |

## License

MIT License - Copyright (c) 2025 Ze Wang

## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [Yosys Documentation](https://yosyshq.readthedocs.io/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [RFC 6455 WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- 野火 EP4CE10_Pro 原理图（`SchematicDiagram/Doc-2-Schematic Diagram of Development Board.pdf`）
