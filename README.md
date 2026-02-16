# Simple VGA Simulator of FPGA

This simulator provides the VGA displayer, a reset button, 4 custom buttons, and 5 LEDs. The reset button is the key "a" on the keyboard. These 4 custom buttons are keys "s", "d", "f", "g" on the keyboard.

## Platform Support

This simulator supports:
- **Linux** (Ubuntu 20.04/22.04 LTS recommended)
- **macOS** (15.0+ Sequoia, tested on Apple Silicon/Darwin 25.0.0)

## How to use

This simulator requires ["Verilator"](https://www.veripool.org/verilator/) and OpenGL.

### Ubuntu / Linux

```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

### macOS

Install Xcode Command Line Tools and Homebrew, then install Verilator:

```bash
# Install Xcode Command Line Tools (includes OpenGL/GLUT framework)
xcode-select --install

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Verilator
brew install verilator
```

> **Note:** On macOS, OpenGL/GLUT is deprecated but still functional. You may see deprecation warnings during compilation, which can be safely ignored.

All you need are ``DevelopmentBoard.v``, ``run_simulation.sh`` and ``simulator.cpp`` files in the ``sim`` folder. When you need to run your simulation, you can follow these steps:

1. Put all your modules in one folder. This simulator does not support IP cores. You need to replace IP cores with your own designs.
2. Insert timescale `` `timescale 1ns / 1ns`` at the beginning of all your module files.
3. Edit ``DevelopmentBoard.v``. Instantiate your module and connect your module to the inputs and outputs of the ``DevelopmentBoard`` module. You cannot edit the module head of the ``DevelopmentBoard`` module.
4. Run ``run_simulation.sh`` with the path of your modules. For example, if the relative path of your modules is ``../RTL``, you can use the following command:

    ```bash
    ./run_simulation.sh ../RTL
    ```


