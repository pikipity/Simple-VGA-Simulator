# Simple VGA Simulator of FPGA

This simulator provides the VGA displayer, a reset button, and 4 custom buttons. The reset button is the key "a" on the keyboard. These 4 custom buttons are keys "s", "d", "f", "g" on the keyboard.

## How to use

This simulator requires ["Verilator"](https://www.veripool.org/verilator/) and OpenGL. You can simply install them in Ubuntu by using following commands:

```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

After install them, you need to go to "sim" folder, and replace "Simple_VGA" module in "DevelopmentBoard.v" with your own module. Note that all your modules should provide the timescale, like `` `timescale 1ns / 1ns``.

Then, run "run_simulation.sh" with the path of your module. For example, if the relative path of your modules is ``../RTL``, you can use the following command:

```bash
./run_simulation.sh ../RTL
```
