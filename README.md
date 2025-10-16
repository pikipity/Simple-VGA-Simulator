# Simple VGA Simulator of FPGA

This simulator provides the VGA displayer, a reset button, 4 custom buttons, and 5 LEDs. The reset button is the key "a" on the keyboard. These 4 custom buttons are keys "s", "d", "f", "g" on the keyboard.

## How to use

This simulator requires ["Verilator"](https://www.veripool.org/verilator/) and OpenGL. You can simply install them in Ubuntu by using following commands:

```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

All you need are ``DevelopmentBoard.v``, ``run_simulation.sh`` and ``simulator.cpp`` files in the ``sim`` folder. When you need to run your simulation, you can follow these steps:

1. Put all your modules in one folder. This simulator does not support IP cores. You need to replace IP cores with your own designs.
2. Insert timescale `` `timescale 1ns / 1ns`` at the beginning of all your module files.
3. Edit ``DevelopmentBoard.v``. Instantiate your module and connect your module to the inputs and outputs of the ``DevelopmentBoard`` module. You cannot edit the module head of the ``DevelopmentBoard`` module.
4. Run ``run_simulation.sh`` with the path of your modules. For example, if the relative path of your modules is ``../RTL``, you can use the following command:

    ```bash
    ./run_simulation.sh ../RTL
    ```

You can try the example by going to ``Example/sim`` folder and then runing the above command. You will see a ball in the center of the VGA screen. When you press "a", all system will be reset. When you press "s", the ball will go up, and the LED 1 will be turned on. When you press "d", the ball will go down, and LED 2 will be turned on. When you press "f", the ball will go left, and LED 3 will be turned on. When you press "g", the ball will go right, and LED 4 will be turned on. 

