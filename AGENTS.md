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
│   ├── DevelopmentBoard.v        # Top-level Verilog wrapper module
│   ├── simulator.cpp             # C++ simulation wrapper with OpenGL
│   ├── run_simulation.sh         # Build and run script
│   └── PinPlanner.py             # GUI tool for pin mapping (optional)
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
- Windows users need VirtualBox with Ubuntu or WSL2 with X11 forwarding

### Required Packages
```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

For users in mainland China, use Tsinghua mirror for apt sources.

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

## Helper Tool: PinPlanner.py

A Python GUI tool (requires tkinter) to automatically generate `DevelopmentBoard.v` with proper signal mapping.

### Usage
```bash
python3 PinPlanner.py
```

### Steps
1. Click "Browse Verilog File" to select your top-level module
2. Map development board pins to your module signals using dropdowns
3. Click "Save Pins" to generate `DevelopmentBoard.v`

**Note**: After generation, remember to add `timescale 1ns / 1ns` to all your module files.

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
| `verilator: command not found` | Install verilator: `sudo apt install verilator` |
| `GL/glut.h: No such file` | Install OpenGL/GLUT: `sudo apt install libglu1-mesa-dev freeglut3-dev mesa-common-dev` |
| `obj_dir/VDevelopmentBoard.mk: No such file` | Verilation failed. Check Verilog syntax and include paths |
| Black screen / no display | Check VGA timing parameters match specification |
| Buttons not responding | Ensure button inputs are active-low (0 when pressed) |

### Display Issues on WSL

If using WSL on Windows, ensure X11 forwarding is configured:
1. Install VcXsrv or Xming on Windows host
2. Set `DISPLAY` environment variable in WSL
3. Allow X11 forwarding through Windows Firewall

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

## License

MIT License - Copyright (c) 2025 Ze Wang

## References

- [Verilator Documentation](https://www.veripool.org/verilator/)
- [VGA Timing Specification](http://www.tinyvga.com/vga-timing/640x480@60Hz)
- [OpenGL/GLUT Documentation](https://www.opengl.org/)
