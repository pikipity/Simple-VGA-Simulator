# Simple VGA Simulator

A Verilator-based FPGA VGA simulation environment for testing VGA controller designs without physical hardware.

## Features

- 🖥️ **Virtual VGA Display** - 640×480 @ 60Hz, RGB565 16-bit color
- 🎮 **5 Virtual Buttons** - Keyboard `a` (reset), `s/d/f/g` (custom)
- 💡 **5 Virtual LEDs** - Visual output indicators
- 🚀 **GUI Launcher** - One-click simulation with automatic compilation and signal mapping
- ⚡ **Real-time Simulation** - Based on Verilator + SDL2 with interactive debugging

## Specifications

| Parameter | Value |
|-----------|-------|
| Resolution | 640 × 480 |
| Refresh Rate | 60 Hz |
| Color Format | RGB565 (16-bit) |
| System Clock | 50 MHz |

## Platform Support

| Platform | Version | Tested Environment |
|----------|---------|-------------------|
| Linux | Ubuntu 22.04+ | GCC + Verilator |
| macOS | 15.0+ (Sequoia) | Apple Silicon, Clang |
| Windows | 10/11 | WSL2 / Native (MSYS2) |

## Prerequisites

### 1. Simulation Environment (Required)

Regardless of using GUI or command line, the following tools must be installed:

| Tool | Ubuntu / Debian | macOS | Windows (WSL2 / MSYS2) |
|------|-----------------|-------|------------------------|
| **Verilator** | `sudo apt install verilator` | `brew install verilator` | `pacman -S verilator` |
| **SDL2** | `sudo apt install libsdl2-dev` | `brew install sdl2` | `pacman -S sdl2` |
| **make + g++** | `sudo apt install build-essential` | `xcode-select --install` | `pacman -S make gcc` |

**Verify installation:**
```bash
verilator --version      # Should show 4.0+
sdl2-config --version    # Should show 2.0+
make --version           # Should show 3.81+
g++ --version            # Should show 7.0+
```

### 2. GUI Launcher (Optional)

- **Option A: Download Pre-built Package (Recommended)**  
  Download the corresponding platform archive from [GitHub Releases](../../releases). Extract and run directly — no Flutter SDK required.

- **Option B: Build GUI from Source**  
  Install [Flutter SDK](https://docs.flutter.dev/get-started/install) (Stable channel, 3.0+). Then:
  ```bash
  cd gui
  flutter pub get
  flutter run -d windows   # or macos / linux
  ```


## Quick Start

### Option 1: GUI Launcher (Recommended)

The easiest way to run simulations without touching the command line.

**Step 1:** Download the pre-built package

Visit [GitHub Releases](../../releases) and download `vga-launcher-<platform>.zip` / `.tar.gz` for your system.

**Step 2:** Extract and run

| Platform | Run Command |
|----------|-------------|
| Windows | Double-click `vga_launcher.exe` |
| macOS | Right-click `VGA Launcher.app` → Open |
| Linux | `./vga_launcher` |

**Step 3:** Use the GUI

1. **Select Project Directory** — Choose the folder containing your `.v` files
2. **Select Top Module** — Pick the top-level module from the dropdown
3. **Signal Mapping** — Automatically inferred; adjust manually if needed
4. **🚀 Run Simulation** — Click to compile and launch the VGA window

> The GUI automatically creates a `sim/` folder inside your project, generates `DevelopmentBoard.v`, and handles the entire compilation process transparently.

---

### Option 2: Command Line (Advanced)

For users who prefer terminal or need CI/CD integration.

**Run Example:**
```bash
cd Example/Example_1_ColorBar/sim
chmod +x run_simulation.sh
./run_simulation.sh ../RTL
```

**Use with Your Own Project:**

Organize your files as:
```
your_project/
├── RTL/
│   └── your_module.v        # Your Verilog files
└── sim/                       # Auto-created by GUI, or copy manually
    ├── DevelopmentBoard.v
    ├── simulator.cpp
    └── run_simulation.sh
```

Run:
```bash
# If RTL is in parent directory
./run_simulation.sh ../RTL

# If RTL is in current directory
./run_simulation.sh
```

## Project Structure

```
Simple-VGA-Simulator/
├── gui/                    # Flutter GUI Launcher (recommended)
│   ├── lib/                # Dart source code
│   ├── assets/             # Templates (simulator.cpp, run_simulation.sh)
│   └── pubspec.yaml
├── sim/                    # Core simulation files (CLI)
│   ├── PinPlanner.py       # Legacy GUI tool (CLI backup)
│   ├── DevelopmentBoard.v  # Top-level wrapper template
│   ├── simulator.cpp       # C++ simulation main
│   └── run_simulation.sh   # Build & run script
├── Example/                # Example projects
│   ├── Example_1_ColorBar/ # Static color bar demo
│   └── Example_2_BallMove/ # Interactive ball movement
├── SchematicDiagram/       # Documentation diagrams
└── Manual for EIE330 Students.md  # Detailed student manual
```

## GUI vs CLI

| | GUI Launcher | Command Line |
|---|--------------|--------------|
| **Difficulty** | ⭐ Zero-config | ⭐⭐⭐ Manual setup |
| **Signal Mapping** | Visual dropdowns | Edit `DevelopmentBoard.v` manually |
| **Compilation** | One-click, transparent | Run `./run_simulation.sh` |
| **Best For** | Students, beginners | CI/CD, advanced users |
| **Requirements** | Simulation environment only | Simulation environment + terminal |

## Key Mappings

| Key | Signal | Function | Active Level |
|-----|--------|----------|--------------|
| `a` | reset | System reset | Low (pressed = 0) |
| `s` | B2 | Custom button 2 | Low |
| `d` | B3 | Custom button 3 | Low |
| `f` | B4 | Custom button 4 | Low |
| `g` | B5 | Custom button 5 | Low |

## License

[MIT License](LICENSE) © 2025 Ze Wang

## Student Manual Documentation

- [Detailed Student Manual](Manual%20for%20EIE330%20Students.md) - Complete tutorial for EIE330 students
