#!/bin/bash

# WSL 鏄剧ず鐜鑷姩閰嶇疆锛堝繀椤诲湪浠讳綍鍛戒护涔嬪墠锛?
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

# 鐢ㄦ硶: ./run_simulation.sh [include_directory_path]

# 妫€娴嬫搷浣滅郴缁?
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

# 鑾峰彇鑴氭湰鎵€鍦ㄧ殑缁濆璺緞
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 璁剧疆榛樿璺緞涓鸿剼鏈墍鍦ㄧ洰褰?
DEFAULT_INCLUDE_DIR="$SCRIPT_DIR"

# 妫€鏌ョ敤鎴锋槸鍚︽彁渚涗簡璺緞鍙傛暟
if [ $# -eq 0 ]; then
    # 鐢ㄦ埛娌℃湁鎻愪緵鍙傛暟锛屼娇鐢ㄨ剼鏈墍鍦ㄨ矾寰?
    INCLUDE_DIR="$DEFAULT_INCLUDE_DIR"
    echo "NOTE: No include directory path is provided, the directory where the script is located is used: $INCLUDE_DIR"
else
    # 鐢ㄦ埛鎻愪緵浜嗗弬鏁帮紝浣跨敤鐢ㄦ埛鎸囧畾鐨勮矾寰?
    INCLUDE_DIR="$1"
    
    # 妫€鏌ョ敤鎴锋彁渚涚殑璺緞鏄惁瀛樺湪
    if [ ! -d "$INCLUDE_DIR" ]; then
        echo "Error: '$INCLUDE_DIR' does not exist"
        echo "Tip: You can use the directory where the script is located without providing any parameters, or provide a valid directory path"
        exit 1
    fi
fi

echo "Start simulation..."
echo "Include directories used: $INCLUDE_DIR"

# 妫€鏌ュ繀瑕佺殑鏂囦欢鏄惁瀛樺湪[6](@ref)
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
        echo "鉁?Sucessfully remove $OBJ_DIR "
    else
        echo "Warning: Problem encountered while deleting $OBJ_DIR folder, but continuing the process..."
    fi
else
    echo "Tip: The $OBJ_DIR folder does not exist, no need to clean it up"
fi


# 绗竴姝ワ細浣跨敤Verilator缂栬瘧Verilog浠ｇ爜
echo "---------------------------------"
echo "Step 1: Run Verilator Compiler..."
VERILATOR_OUTPUT=$(verilator -Wall --cc --exe -I"$INCLUDE_DIR" simulator.cpp DevelopmentBoard.v $LDFLAGS -CFLAGS "$SDL_CFLAGS")
VERILATOR_EXIT_CODE=$?

echo "$VERILATOR_OUTPUT"

# 妫€鏌erilator鏄惁鎴愬姛鎵ц
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

echo "鉁?Verilator compilation completed successfully!"

# 绗簩姝ワ細鏋勫缓浠跨湡鍙墽琛屾枃浠?
echo "---------------------------------"
echo "Step 2: Build the simulation executable..."
# Export SDL flags for make
export CXXFLAGS="$SDL_CFLAGS"
make -j -C obj_dir -f VDevelopmentBoard.mk VDevelopmentBoard

# 妫€鏌ake鏄惁鎴愬姛鏋勫缓
if [ $? -ne 0 ]; then
    echo "Error: Make build failed!"
    echo "Please check the compilation error message above"
    exit 1
fi

echo "鉁?Simulation executable file built successfully!"

# 绗笁姝ワ細杩愯浠跨湡
echo "---------------------------------"
echo "Step 3: Start the simulation..."
echo "----------------------------------------"
obj_dir/VDevelopmentBoard

# 妫€鏌ヤ豢鐪熸槸鍚︽垚鍔熻繍琛?
SIMULATION_EXIT_CODE=$?
echo "----------------------------------------"

if [ $SIMULATION_EXIT_CODE -ne 0 ]; then
    echo "WARNING: Simulation execution exit code: $SIMULATION_EXIT_CODE"
else
    echo "鉁?Simulation execution completed!"
fi