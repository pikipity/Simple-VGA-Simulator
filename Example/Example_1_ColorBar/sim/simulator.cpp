//#include <verilated.h>          // defines common routines
// Platform-specific GLUT header and platform detection
#if defined(__APPLE__)
    #define PLATFORM_MACOS 1
    #include <GLUT/glut.h>
#elif defined(__linux__) || defined(__linux) || defined(linux)
    #define PLATFORM_LINUX 1
    #include <GL/glut.h>
    // freeglut extensions for window close callback
    #ifdef GLUT_API_VERSION
        #include <GL/freeglut_ext.h>
    #else
        #warning "Using original GLUT - window close button may not work properly. Consider installing freeglut."
    #endif
#else
    #error "Unsupported platform - only macOS and Linux are supported"
#endif
#include <thread>
#include <iostream>
#include <atomic>
#include <cstring>
#include <chrono>
#include "VDevelopmentBoard.h"            // from Verilating "display.v"

using namespace std;

// Cross-platform quit flag and global thread handle
static std::atomic<bool> g_quit_requested{false};
static std::thread g_sim_thread;
static std::atomic<bool> g_cleanup_done{false};  // Prevent reentrant cleanup

// Cleanup function called on exit or window close
void cleanup_simulation() {
    // Prevent double-join in case of concurrent calls
    if (g_cleanup_done.exchange(true, std::memory_order_acq_rel)) {
        return;
    }
    g_quit_requested.store(true, std::memory_order_release);
    if (g_sim_thread.joinable()) {
        g_sim_thread.join();
    }
}

// Real-time synchronization class
// Synchronizes simulation time with wall clock time
class RealTimeSync {
    std::chrono::steady_clock::time_point epoch;
    uint64_t sim_cycles = 0;
    static constexpr uint64_t NS_PER_CYCLE = 80;  // 12.5MHz = 80ns/cycle (reduced for better performance)
    
public:
    RealTimeSync() : epoch(std::chrono::steady_clock::now()) {}
    
    // Reset time baseline - call after initialization is complete
    void reset() {
        epoch = std::chrono::steady_clock::now();
        sim_cycles = 0;
    }
    
    void tick() {
        sim_cycles++;
        uint64_t target_ns = sim_cycles * NS_PER_CYCLE;
        
        auto now = std::chrono::steady_clock::now();
        auto elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            now - epoch).count();
        
        if (target_ns > elapsed_ns) {
            // Busy-wait until real time catches up to simulation time
            auto target = now + std::chrono::nanoseconds(target_ns - elapsed_ns);
            while (std::chrono::steady_clock::now() < target) {
                #if defined(__x86_64__)
                    __builtin_ia32_pause();           // Intel/AMD x86_64: reduce power/contention
                #elif defined(__aarch64__) || defined(_M_ARM64)
                    __asm__ __volatile__("yield");    // ARM64 (Apple Silicon, etc.): yield CPU
                #endif
            }
        } else if (elapsed_ns - target_ns > 1000000) {
            // Only warn if lag is more than 1ms to avoid spam
            std::cerr << "Simulation lag: " << (elapsed_ns - target_ns) << "ns\n";
        }
    }
};

static RealTimeSync g_sync;

void wait_10ns() {
    g_sync.tick();
}

VDevelopmentBoard* display;              // instantiation of the model

uint64_t main_time = 0;         // current simulation time
double sc_time_stamp() {        // called by $time in Verilog
    return main_time;
}

// to wait for the graphics thread to complete initialization
std::atomic<bool> gl_setup_complete{false};

// 640X480 VGA sync parameters
const int LEFT_PORCH        =     48;
const int ACTIVE_WIDTH        =     640;
const int RIGHT_PORCH        =     16;
const int HORIZONTAL_SYNC    =    96;
const int TOTAL_WIDTH        =    800;

const int TOP_PORCH            =     33;
const int ACTIVE_HEIGHT        =     480;
const int BOTTOM_PORCH        =     10;
const int VERTICAL_SYNC        =    2;
const int TOTAL_HEIGHT        =    525;

// Active region offsets
const int H_ACTIVE_START = 144; // H_SYNC(96) + H_BACK(40) + H_LEFT(8) from Verilog
const int V_ACTIVE_START = 35;  // V_SYNC(2) + V_BACK(25) + V_TOP(8) from Verilog

// pixels are buffered here - double buffering for thread safety
// 一维数组布局: [x * ACTIVE_HEIGHT * 3 + y * 3 + channel]
static float buffer_a[ACTIVE_WIDTH * ACTIVE_HEIGHT * 3] = {};
static float buffer_b[ACTIVE_WIDTH * ACTIVE_HEIGHT * 3] = {};

// RGB565 to float lookup tables for fast conversion
static float RGB5_TO_FLOAT[32];   // 5-bit (0-31) -> float (0.0-1.0)
static float RGB6_TO_FLOAT[64];   // 6-bit (0-63) -> float (0.0-1.0)

// Initialize RGB lookup tables
void init_rgb_lookup_tables() {
    for (int i = 0; i < 32; i++) {
        RGB5_TO_FLOAT[i] = float(i) / 31.0f;
    }
    for (int i = 0; i < 64; i++) {
        RGB6_TO_FLOAT[i] = float(i) / 63.0f;
    }
}
static std::atomic<float*> write_buffer{buffer_a};  // 模拟线程写入
static std::atomic<float*> read_buffer{buffer_b};   // GLUT线程读取
static std::atomic<bool> buffer_swap_pending{false}; // 新帧就绪标记

// calculating each pixel's size in accordance to OpenGL system
// each axis in OpenGL is in the range [-1:1]
// 重新计算VGA像素大小，保持原始比例
float pixel_w = 2.0 / ACTIVE_WIDTH * 0.8f;
float pixel_h = 2.0 / ACTIVE_HEIGHT * 0.8f;

std::atomic<bool> restart_triggered{false};

// 在全局变量区域添加LED状态变量
std::atomic<int> leds_state[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态

// Window close callback for Linux (freeglut)
#ifdef PLATFORM_LINUX
void window_close_handler() {
    cleanup_simulation();
    glutLeaveMainLoop();
}
#endif

const int WINDOW_WIDTH = 800;  // 窗口宽度
const int WINDOW_HEIGHT = 600; // 窗口高度
const int VGA_DISPLAY_HEIGHT = 480; // VGA显示区域高度
const int LED_DISPLAY_HEIGHT = 100; // LED显示区域高度

// 添加圆形绘制函数
void drawCircle(float cx, float cy, float r, int num_segments) {
    glBegin(GL_TRIANGLE_FAN);
    for(int i = 0; i < num_segments; i++) {
        float theta = 2.0f * 3.1415926f * float(i) / float(num_segments);
        float x = r * cosf(theta);
        float y = r * sinf(theta);
        glVertex2f(x + cx, y + cy);
    }
    glEnd();
}

// gets called periodically to update screen
void render(void) {
    glClear(GL_COLOR_BUFFER_BIT);

    // 绘制VGA显示区域背景
    glColor3f(0.1f, 0.1f, 0.1f);
    glRectf(-1.0f, -1.0f, 1.0f, 1.0f);

    // 绘制VGA显示区域标题
    glColor3f(1.0f, 1.0f, 1.0f);
    glRasterPos2f(-0.9f, 0.9f);
    std::string vga_title = "VGA screen";
    for (char c : vga_title) {
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, c);
    }
    
    // 检查是否有新帧就绪，交换缓冲区
    if (buffer_swap_pending.exchange(false, std::memory_order_acquire)) {
        float* old_write = write_buffer.exchange(
            read_buffer.exchange(
                write_buffer.load(std::memory_order_relaxed),
                std::memory_order_relaxed
            ),
            std::memory_order_relaxed
        );
        (void)old_write; // 抑制未使用警告
    }
    
    float* buf = read_buffer.load(std::memory_order_acquire);
    
    // convert pixels into OpenGL rectangles
    for(int i = 0; i < ACTIVE_WIDTH; i++){
        for(int j = 0; j < ACTIVE_HEIGHT; j++){
            int idx = ((i * ACTIVE_HEIGHT) + j) * 3;
            glColor3f(buf[idx], buf[idx + 1], buf[idx + 2]);
            // 调整VGA显示位置，使其位于VGA区域中心
            float x1 = (i * pixel_w - 0.8f) * 0.8f;
            float y1 = (-j * pixel_h + 0.6f) * 0.8f+0.3f;
            float x2 = ((i+1) * pixel_w - 0.8f) * 0.8f;
            float y2 = (-(j+1) * pixel_h + 0.6f) * 0.8f+0.3f;
            glRectf(x1, y1, x2, y2);
        }
    }

    // 绘制LED显示区域背景
    glColor3f(0.2f, 0.2f, 0.2f);
    glRectf(-1.0f, -1.0f, 1.0f, -0.8f);

    // 绘制LED显示区域标题
    glColor3f(1.0f, 1.0f, 1.0f);
    glRasterPos2f(-0.9f, -0.85f);
    std::string led_title = "LED";
    for (char c : led_title) {
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, c);
    }

    // 绘制LED
    float led_spacing = 1.6f / 6.0f; // LED之间的间距
    float led_radius = 0.04f;        // LED半径
    
    for(int i = 0; i < 5; i++){
        float x_pos = -0.8f + (i+1) * led_spacing;
        float y_pos = -0.9f;
        
        // 绘制LED底座
        glColor3f(0.3f, 0.3f, 0.3f);
        drawCircle(x_pos, y_pos, led_radius * 1.2f, 20);
        
        // 根据状态绘制LED
        if(leds_state[i] == 0){
            // LED亮
            glColor3f(1.0f, 0.0f, 0.0f); // 红色
        } else {
            // LED灭
            glColor3f(0.1f, 0.0f, 0.0f); // 暗红色
        }
        drawCircle(x_pos, y_pos, led_radius, 20);
        
        // 绘制LED编号
        glColor3f(1.0f, 1.0f, 1.0f);
        glRasterPos2f(x_pos - 0.01f, y_pos - 0.06f);
        glutBitmapCharacter(GLUT_BITMAP_9_BY_15, '1' + i);
    }
    
    glFlush();
}

// timer to periodically update the screen
void glutTimer(int t) {
    glutPostRedisplay(); // re-renders the screen
    glutTimerFunc(t, glutTimer, t);
}

// handle up/down/left/right arrow keys
std::atomic<int> keys[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态
// int key_prev_state[5] = {1, 1, 1, 1, 1};
void keyPressed(unsigned char key, int x, int y) {
    switch(key) {
        case 'a':
            keys[0] = 0;
            restart_triggered.store(true, std::memory_order_release);
            break;
        case 's':
            keys[1] = 0;
            break;
        case 'd':
            keys[2] = 0;
            break;
        case 'f':
            keys[3] = 0;
            break;
        case 'g':
            keys[4] = 0;
            break;
        // Exit handlers: ESC (27), 'q', or 'Q'
        case 27:
        case 'q':
        case 'Q':
            cleanup_simulation();
#if defined(PLATFORM_LINUX)
            glutLeaveMainLoop();
#elif defined(PLATFORM_MACOS)
            exit(0);
#endif
            break;
    }
}

void keyReleased(unsigned char key, int x, int y) {
    switch(key) {
        case 'a':
            keys[0] = 1;
            break;
        case 's':
            keys[1] = 1;
            break;
        case 'd':
            keys[2] = 1;
            break;
        case 'f':
            keys[3] = 1;
            break;
        case 'g':
            keys[4] = 1;
            break;
    }
}

// initiate and handle graphics
void graphics_loop(int argc, char** argv) {
    glutInit(&argc, argv);
    glutInitDisplayMode(GLUT_SINGLE);
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT);
    glutInitWindowPosition(100, 100);
    glutCreateWindow("VGA and LED Simulator (Press ESC or Q to exit)");
    glutDisplayFunc(render);
    glutSetKeyRepeat(GLUT_KEY_REPEAT_OFF);
    glutKeyboardFunc(keyPressed);
    glutKeyboardUpFunc(keyReleased);
    
    // Platform-specific window close handling
#if defined(PLATFORM_MACOS)
    // macOS: glutMainLoop() never returns, use atexit for cleanup
    atexit(cleanup_simulation);
#elif defined(PLATFORM_LINUX)
    // Linux (freeglut): configure to continue execution after window close
    #ifdef GLUT_ACTION_ON_WINDOW_CLOSE
        glutSetOption(GLUT_ACTION_ON_WINDOW_CLOSE, GLUT_ACTION_CONTINUE_EXECUTION);
    #endif
    // Warn if GLUT version does not support window close callback
    #if (!defined(GLUT_API_VERSION) || GLUT_API_VERSION < 4) && !defined(GLUT_HAS_CLOSE_CALLBACK)
        #warning "GLUT version does not support window close callback. Use ESC or Q key to exit."
    #endif
    // Register window close callback
    // Use GLUT_API_VERSION >= 4 for freeglut 2.4+, fallback to GLUT_HAS_CLOSE_CALLBACK
    #if defined(GLUT_API_VERSION) && GLUT_API_VERSION >= 4
        glutCloseFunc(window_close_handler);
    #elif defined(GLUT_HAS_CLOSE_CALLBACK)
        glutCloseFunc(window_close_handler);
    #endif
#endif

    gl_setup_complete.store(true, std::memory_order_release);

    // re-render every 16ms, around 60Hz
    glutTimerFunc(16, glutTimer, 16);
    glutMainLoop();
}

// tracking VGA signals
int coord_x = 0;
int coord_y = 0;
bool pre_h_sync = 0;
bool pre_v_sync = 0;

// set Verilog module inputs based on arrow key inputs
void apply_input() {
    display->reset = keys[0];
    display->B2 = keys[1];
    display->B3 = keys[2];
    display->B4 = keys[3];
    display->B5 = keys[4];
}

void update_leds(){
    leds_state[0].store(display->led1);
    leds_state[1].store(display->led2);
    leds_state[2].store(display->led3);
    leds_state[3].store(display->led4);
    leds_state[4].store(display->led5);
}

void display_eval(){
    apply_input();
    display->eval();
    update_leds();
}
// simulate for a single clock
void tick() {
    wait_10ns();
    main_time++;
    display->clk = 1;
    display_eval();
    
    // 下降沿
    wait_10ns();
    main_time++;
    display->clk = 0;
    display_eval();
}

// globally reset the model
void reset() {
    display->reset = 0; // 复位信号初始为高电平（不复位）
    display->B2 = 1;
    display->B3 = 1;
    display->B4 = 1;
    display->B5 = 1;
    display->clk = 0;
    display->eval();
    for(int i = 0; i < 10; i++) {
        tick();
    }
    display->reset = 1;
    
    // Clear graphics buffers
    std::memset(buffer_a, 0, sizeof(buffer_a));
    std::memset(buffer_b, 0, sizeof(buffer_b));
     
    // Reset VGA signal tracking variables
    coord_x = 0;
    coord_y = 0;
    pre_h_sync = 0;
    pre_v_sync = 0;
    
    // Reset key states
    for (int i = 0; i < 5; i++) {
        keys[i].store(1);
    }
    
    // Reset LED states
    for (int i = 0; i < 5; i++) {
        leds_state[i].store(1);
    }
}

// read VGA outputs and update graphics buffer
void sample_pixel() {
    
    coord_x = (coord_x + 1) % TOTAL_WIDTH;

    if(display->h_sync && !pre_h_sync){ // on positive edge of h_sync (active high)
        // re-sync horizontal counter: reset to 0 and increment vertical counter
        coord_x = 0;
        coord_y = (coord_y + 1) % TOTAL_HEIGHT;
    }

    if(display->v_sync && !pre_v_sync){ // on positive edge of v_sync (active high)
        // re-sync vertical counter: reset to 0
        coord_y = 0;
    }

    if(coord_x >= H_ACTIVE_START && coord_x < H_ACTIVE_START + ACTIVE_WIDTH && 
       coord_y >= V_ACTIVE_START && coord_y < V_ACTIVE_START + ACTIVE_HEIGHT){
        int x_index = coord_x - H_ACTIVE_START;
        int y_index = coord_y - V_ACTIVE_START;
        int rgb = display->rgb;
        float* buf = write_buffer.load(std::memory_order_relaxed);
        int idx = ((x_index * ACTIVE_HEIGHT) + y_index) * 3;
        // Use lookup tables for fast RGB565 to float conversion
        buf[idx] = RGB5_TO_FLOAT[(rgb >> 11) & 0x1F];      // Red (5-bit)
        buf[idx + 1] = RGB6_TO_FLOAT[(rgb >> 5) & 0x3F];   // Green (6-bit)
        buf[idx + 2] = RGB5_TO_FLOAT[rgb & 0x1F];          // Blue (5-bit)
    }

    // 垂直同步上升沿时标记缓冲区可交换
    if(display->v_sync && !pre_v_sync){
        buffer_swap_pending.store(true, std::memory_order_release);
    }

    pre_h_sync = display->h_sync;
    pre_v_sync = display->v_sync;
}
// simulation thread function
void simulation_loop() {
    // Initialize RGB lookup tables
    init_rgb_lookup_tables();
    
    // wait for graphics initialization to complete
    while (!gl_setup_complete.load(std::memory_order_acquire)) {
        std::this_thread::yield();
    }

    // create the model
    display = new VDevelopmentBoard;

    // reset the model
    reset();
    
    // Reset time baseline after initialization is complete
    // This avoids false "Simulation lag" warnings from idle time during startup
    g_sync.reset();

    // cycle accurate simulation loop - also checks quit flag
    while (!Verilated::gotFinish() && !g_quit_requested.load(std::memory_order_acquire)) {
        if (restart_triggered.exchange(false, std::memory_order_acquire)) {
            reset();
        }
        
        tick();
        tick();
        // the clock frequency of VGA is half of that of the whole model
        // so we sample from VGA every other clock
        sample_pixel();
    }

    display->final();
    delete display;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);   // remember args

    // On macOS, GLUT must run on the main thread
    // So we create a thread for simulation instead
    g_sim_thread = std::thread(simulation_loop);

    // Run GLUT on the main thread (blocks on macOS, may return on Linux)
    graphics_loop(argc, argv);

    // Cleanup simulation thread
    // On macOS: this is also called via atexit, but duplicate join is safe
    // On Linux: glutMainLoop returns after window close, cleanup here
    cleanup_simulation();
    
    return 0;
}
