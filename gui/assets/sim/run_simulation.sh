#!/bin/bash

# WSL display environment auto-configuration (must be before any command)
if grep -qi microsoft /proc/version 2>/dev/null; then
    if [ -z "$DISPLAY" ]; then
        export DISPLAY=:0
    fi
    if [ -z "$XDG_RUNTIME_DIR" ]; then
        export XDG_RUNTIME_DIR=/tmp/runtime-$UID
        mkdir -p $XDG_RUNTIME_DIR
    fi
    if [ -z "$WAYLAND_DISPLAY" ] && [ -S "$XDG_RUNTIME_DIR/wayland-0" ]; then
        export WAYLAND_DISPLAY=wayland-0
    fi
fi

# Usage: ./run_simulation.sh [include_directory_path]

# Detect operating system
OS=$(uname -s)
echo "Detected OS: $OS"

# Detect SDL2 with multiple fallback paths
SDL_CONFIG=""
for path in sdl2-config /opt/homebrew/bin/sdl2-config /usr/local/bin/sdl2-config /usr/bin/sdl2-config; do
    if command -v "$path" &> /dev/null; then
        SDL_CONFIG="$path"
        break
    fi
done

if [ -n "$SDL_CONFIG" ]; then
    SDL_CFLAGS=$($SDL_CONFIG --cflags)
    SDL_LIBS=$($SDL_CONFIG --libs)
    echo "Found SDL2: $SDL_CONFIG"
    echo "SDL CFLAGS: $SDL_CFLAGS"
    echo "SDL LIBS: $SDL_LIBS"
else
    echo "Warning: sdl2-config not found, using default flags"
    # Fallback for common paths
    SDL_CFLAGS="-I/usr/include/SDL2 -D_REENTRANT"
    SDL_LIBS="-lSDL2"
fi

# Set LDFLAGS for Verilator (prepend -LDFLAGS to each flag)
LDFLAGS=""
for flag in $SDL_LIBS; do
    LDFLAGS="$LDFLAGS -LDFLAGS $flag"
done

# Get the absolute path of the script directory
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Set default path to the script directory
DEFAULT_INCLUDE_DIR="$SCRIPT_DIR"

# Check if user provided a path argument
if [ $# -eq 0 ]; then
    # User did not provide an argument, use the script directory
    INCLUDE_DIR="$DEFAULT_INCLUDE_DIR"
    echo "NOTE: No include directory path is provided, the directory where the script is located is used: $INCLUDE_DIR"
else
    # User provided an argument, use the specified path
    INCLUDE_DIR="$1"
    
    # Check if the provided path exists
    if [ ! -d "$INCLUDE_DIR" ]; then
        echo "Error: '$INCLUDE_DIR' does not exist"
        echo "Tip: You can use the directory where the script is located without providing any parameters, or provide a valid directory path"
        exit 1
    fi
fi

echo "Start simulation..."
echo "Include directories used: $INCLUDE_DIR"

# Check if required files exist
if [ ! -f "simulator.cpp" ]; then
    echo "Error: simulator.cpp does not exist in the current directory"
    exit 1
fi

if [ ! -f "DevelopmentBoard.v" ]; then
    echo "Error: DevelopmentBoard.v does not exist in the current directory"
    exit 1
fi

echo "---------------------------------"
echo "Step 0: Clean up previously generated files..."
OBJ_DIR="obj_dir"

if [ -d "$OBJ_DIR" ]; then
    echo "Remove $OBJ_DIR ..."
    if rm -rf "$OBJ_DIR"; then
        echo "✓ Sucessfully remove $OBJ_DIR "
    else
        echo "Warning: Problem encountered while deleting $OBJ_DIR folder, but continuing the process..."
    fi
else
    echo "Tip: The $OBJ_DIR folder does not exist, no need to clean it up"
fi


# Step 1: Compile Verilog code with Verilator
echo "---------------------------------"
echo "Step 1: Run Verilator Compiler..."
VERILATOR_OUTPUT=$(verilator -Wall --cc --exe -I"$INCLUDE_DIR" simulator.cpp DevelopmentBoard.v $LDFLAGS -CFLAGS "$SDL_CFLAGS")
VERILATOR_EXIT_CODE=$?

echo "$VERILATOR_OUTPUT"

# Check if Verilator executed successfully
if [ ! -f "obj_dir/VDevelopmentBoard.mk" ]; then
    echo "Error: Verilator compilation failed!"
    echo "Possible causes:"
    echo "1. Not provide correct path of RTLs"
    echo "2. Verilator is not installed"
    echo "   - Ubuntu: sudo apt install build-essential verilator"
    echo "   - macOS:  brew install verilator"
    echo "3. SDL2 is not installed"
    echo "   - Ubuntu: sudo apt install libsdl2-dev"
    echo "   - macOS:  brew install sdl2"
    echo "4. The code contains syntax errors"
    exit 1
fi

echo "✓ Verilator compilation completed successfully!"

# Step 2: Build simulation executable
echo "---------------------------------"
echo "Step 2: Build the simulation executable..."
# Export SDL flags for make
export CXXFLAGS="$SDL_CFLAGS"
make -j -C obj_dir -f VDevelopmentBoard.mk VDevelopmentBoard

# Check if make built successfully
if [ $? -ne 0 ]; then
    echo "Error: Make build failed!"
    echo "Please check the compilation error message above"
    exit 1
fi

echo "✓ Simulation executable file built successfully!"

# Step 3: Run simulation
echo "---------------------------------"
echo "Step 3: Start the simulation..."
echo "----------------------------------------"
obj_dir/VDevelopmentBoard

# Check if simulation ran successfully
SIMULATION_EXIT_CODE=$?
echo "----------------------------------------"

if [ $SIMULATION_EXIT_CODE -ne 0 ]; then
    echo "WARNING: Simulation execution exit code: $SIMULATION_EXIT_CODE"
else
    echo "✓ Simulation execution completed!"
fi