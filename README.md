# Simple VGA Simulator

A Verilator-based FPGA VGA simulation environment for testing VGA controller designs without physical hardware.

## Features

- 🖥️ **Virtual VGA Display** - 640×480 @ 60Hz, RGB565 16-bit color
- 🎮 **5 Virtual Buttons** - Keyboard `a` (reset), `s/d/f/g` (custom)
- 💡 **5 Virtual LEDs** - Visual output indicators
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

## Prerequisites

### Ubuntu / Linux

```bash
# Update package lists
sudo apt-get update

# Install build tools
sudo apt-get install build-essential

# Install Verilator
sudo apt-get install verilator

# Install SDL2 libraries
sudo apt-get install libsdl2-dev
```

**Verify installation:**
```bash
# Check Verilator
verilator --version  # Should show version 4.0+

# Check SDL2
sdl2-config --version  # Should show version number (e.g., 2.0.20)
```

### macOS

1. **Install Xcode Command Line Tools** (includes GCC compiler)
   ```bash
   xcode-select --install
   ```

2. **Install Homebrew** (if not already installed)
   
   Visit https://brew.sh and follow the official installation instructions.

3. **Install SDL2**
   ```bash
   brew install sdl2
   ```

4. **Install Verilator**
   ```bash
   brew install verilator
   ```


## Quick Start

### 1. Run Example (2-minute demo)

```bash
# Navigate to example
cd Example/Example_1_ColorBar/sim

# Make executable
chmod +x run_simulation.sh

# Run simulation
./run_simulation.sh ../RTL
```

A VGA window will appear displaying color bars. Press `a` to reset.

### 2. Use with Your Own Project

**Setup:** Copy these 3 files from `sim/` to your project:

```
your_project/
├── sim/
│   ├── DevelopmentBoard.v   # Top-level wrapper
│   ├── simulator.cpp        # C++ simulation main
│   └── run_simulation.sh    # Build & run script
└── RTL/                     # Your Verilog files
    └── your_module.v
```

**Steps:**

| Step | Action | Details |
|------|--------|---------|
| 1 | Organize code | Put all `.v` files in `RTL/` folder. **Note:** IP cores are not supported; replace them with your own designs. |
| 2 | Add timescale | Add `` `timescale 1ns / 1ns`` to the beginning of all module files. |
| 3 | Configure `DevelopmentBoard.v` | **Option A (GUI):** Run `python3 /path/to/PinPlanner.py` to auto-generate.<br>**Option B (Manual):** Edit `DevelopmentBoard.v` to instantiate your module. |
| 4 | Run simulation | Execute `./run_simulation.sh <rtl_path>` |

**Example commands:**

```bash
# If RTL is in parent directory
./run_simulation.sh ../RTL

# If RTL is in current directory
./run_simulation.sh
```

## Project Structure

```
Simple-VGA-Simulator/
├── sim/                    # Core simulation files (required)
│   ├── PinPlanner.py       # GUI tool for auto-generating DevelopmentBoard.v
│   ├── DevelopmentBoard.v  # Top-level wrapper template
│   ├── simulator.cpp       # C++ simulation main
│   └── run_simulation.sh   # Build & run script
├── Example/                # Example projects
│   ├── Example_1_ColorBar/ # Static color bar demo
│   └── Example_2_BallMove/ # Interactive ball movement
├── SchematicDiagram/       # Documentation diagrams
└── Manual for EIE330 Students.md  # Detailed student manual
```

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
