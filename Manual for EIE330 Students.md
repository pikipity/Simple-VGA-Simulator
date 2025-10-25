# Installation & Utilization of VGA Simulator

## 1. Installation

### 1.1 Install Linux System

The simulator requires ["verilator"](https://www.veripool.org/verilator/) and ["OpenGL"](https://www.opengl.org/). These 2 tools can be easily installed in Linux. 

If you use Windows or Mac, you can use ["VirtualBox"](https://www.virtualbox.org/wiki/Downloads) and install ["Ubuntu"](https://ubuntu.com/) in a virtual environment. I recommand using [``Ubuntu 22.04 LTS`` version](https://releases.ubuntu.com/jammy/). If you use the VirtualBox, make sure that you install the ``"VirtualBox Guest Additions"`` and Set up the shared folder. Otherwise, you cannot access your files outside your virtual environment. You may refer the following videos and documents to install and set up "VirtualBox" and "Ubuntu".

+ [How to Install Ubuntu on VirtualBox in Windows](https://www.youtube.com/watch?v=x5MhydijWmc)
+ [How to Install VirtualBox Guest Additions on Ubuntu](https://www.linuxtechi.com/install-virtualbox-guest-additions-on-ubuntu/)
+ [How to set up the shared folders in VirtualBox](https://docs.oracle.com/en/virtualization/virtualbox/6.0/user/sharedfolders.html)

For Windows, besides the VirtualBox, you also can use ``wsl`` to install Ubuntu. But the process is relatively complex. 
If you use ``wsl``, you also need to install and set up ``Xming``.
You may refer the following documents to install ubuntu in ``wsl`` and ``Xming``:

+ [Install wsl distro](https://vpraharsha3.medium.com/installing-wsl-distro-to-a-different-custom-location-30d101f04113)
+ [Install and set up Xming](https://www.uwyo.edu/data-science/resources/knowledge-base/x11-with-windows-subsystem-for-linux.html)

### 1.2 Install Required Tools

I will only show how to install ["verilator"](https://www.veripool.org/verilator/) and ["OpenGL"](https://www.opengl.org/) in Ubuntu. For other linux system, you need to use your own package manager to install these packages. 

(For studnets who are in mainland China, 你需要使用内地的apt源，否则可能安装失败！参考：[清华大学ubuntu | 镜像站使用帮助](https://mirrors.tuna.tsinghua.edu.cn/help/ubuntu/))

In Ubuntu, you can use the following commands to install all what you need

```bash
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install verilator
sudo apt-get install libglu1-mesa-dev freeglut3-dev mesa-common-dev
```

### 1.3 Download Simulator

Go to [Simple-VGA-Simulator](https://github.com/pikipity/Simple-VGA-Simulator.git) and download the whole repository. All your need is in the ``sim`` folder. 

## 2. How to use this Simulator

This simulator provides the VGA displayer, a reset button, and 4 custom buttons.
All you need are ``DevelopmentBoard.v``, ``simulator.cpp``, and ``run_simulation.sh`` in the ``sim`` folder of ``Simple-VGA-Simulator``. 
You can consider that ``DevelopmentBoard.v`` is the development board that you used in our previous labs. 


+ Inputs of Development Board:
    + This development board contains one ``reset`` button and four custom buttons that are ``B2``, ``B3``, ``B4``, and ``B5``. The functions of these buttons are same as the development board that you used in previous labs. When the button is pressed, "0" is input. When the button is released, "1" is input. Note: The ``reset`` button only can be used to reset your system. The reset button is the key "a" on the keyboard. These 4 custom buttons are keys "s", "d", "f", "g" on the keyboard.
    + This development board contains a system clock ``clk``. It works on 50 MHz, which is also same as the development board that you used in previous labs.
+ Outputs of Development Board:
    + This development board contains VGA port pins:  Line synchronization signal pin ``h_sync``, field synchronization signal pin ``v_sync``, and color data pins ``rgb``. The color data also follows the RGB565, which is same as the development board that you used in labs.

1. Make sure that all your own modules are in the same folder and include the timescale. For example, you can add `` `timescale 1ns / 1ns`` at the beginning of all your module files. 
2. Make sure that your modules do not use the IP cores!!! If you use IP cores, implement your own module to replace them.
3. Copy ``DevelopmentBoard.v``, ``simulator.cpp``, and ``run_simulation.sh`` in the ``sim`` folder of ``Simple-VGA-Simulator`` to your simulation folder. 
4. Replace the ``Simple_VGA`` instance in ``DevelopmentBoard.v`` with your own module. 
5. Run ``run_simulation.sh`` with the path of your own modules with the command ``./run_simulation.sh <module_path>``. For example, if your modules are in ``../RTL``, you can run it by ``./run_simulation.sh ../RTL``.


## 3. Appendix: Paths in Linux

In Linux, a path is a string that specifies the location of a file or directory. There are two types of paths:

+ Absolute paths: An absolute path is a path that specifies the exact location of a file or directory, starting from the root directory (/). For example, ``/home/user/documents/file.txt`` is an absolute path that specifies the location of the file ``file.txt`` in the ``documents`` directory inside the ``home`` directory of the ``user`` account.
+ Relative paths: A relative path is a path that specifies the location of a file or directory relative to the current working directory. For example, ``documents/file.txt`` is a relative path that specifies the location of the file ``file.txt`` in the ``documents`` directory inside the current working directory.

To navigate to a different directory in Linux, you can use the cd command followed by the path of the directory:

```bash
cd /home/user/documents
```

You can use the pwd command to print the current working directory:

```bash
pwd
```

You can use the ls command to list all files in the current working directory:

```bash
ls
```

Here are two import relative paths of linux:

+ ``.``: The current directory
+ ``..``: The parent directory of the current directory
