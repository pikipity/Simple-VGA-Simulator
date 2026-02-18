#include <SDL.h>
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

// SDL window and surfaces (forward declaration)
static SDL_Window* g_window = nullptr;
static SDL_Surface* g_vga_surface = nullptr;

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
    
    // Release SDL resources
    if (g_vga_surface) {
        SDL_FreeSurface(g_vga_surface);
        g_vga_surface = nullptr;
    }
    if (g_window) {
        SDL_DestroyWindow(g_window);
        g_window = nullptr;
    }
    SDL_Quit();
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

// Window dimensions (initialized in main(), may differ from requested on HiDPI)
int g_window_width = 800;
int g_window_height = 600;
const int VGA_DISPLAY_WIDTH = 640;
const int VGA_DISPLAY_HEIGHT = 480;
const int LED_AREA_HEIGHT = 100;
const int MARGIN_TOP = 35;      // Space for labels at top
const int MARGIN = 20;          // Margin around display areas

// SDL surfaces (declared above)
static SDL_Surface* g_screen_surface = nullptr;      // Window surface (actual display)

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

std::atomic<bool> restart_triggered{false};

// 在全局变量区域添加LED状态变量
std::atomic<int> leds_state[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态

// Simple 5x3 bitmap font for labels (0 = empty, 1 = pixel)
// Characters: V, G, A, L, E, D
const uint8_t FONT_5x3[][5] = {
    {0b10001, 0b10001, 0b01010, 0b01010, 0b00100}, // V
    {0b01110, 0b10000, 0b10111, 0b10001, 0b01110}, // G
    {0b01110, 0b10001, 0b11111, 0b10001, 0b10001}, // A
    {0b10000, 0b10000, 0b10000, 0b10000, 0b11111}, // L
    {0b11111, 0b10000, 0b11100, 0b10000, 0b11111}, // E
    {0b11110, 0b10001, 0b10001, 0b10001, 0b11110}, // D
};

void draw_char(SDL_Surface* surface, int x, int y, char c, uint32_t color, int scale) {
    int idx = -1;
    switch (c) {
        case 'V': idx = 0; break;
        case 'G': idx = 1; break;
        case 'A': idx = 2; break;
        case 'L': idx = 3; break;
        case 'E': idx = 4; break;
        case 'D': idx = 5; break;
    }
    if (idx < 0) return;
    
    const uint8_t* bitmap = FONT_5x3[idx];
    for (int row = 0; row < 5; row++) {
        for (int col = 0; col < 5; col++) {  // Changed from 3 to 5 columns
            if (bitmap[row] & (1 << (4 - col))) {
                SDL_Rect pixel = {x + col * scale, y + row * scale, scale, scale};
                SDL_FillRect(surface, &pixel, color);
            }
        }
    }
}

void draw_label(SDL_Surface* surface, int x, int y, const char* text, uint32_t color, int scale) {
    int offset = 0;
    while (*text) {
        draw_char(surface, x + offset, y, *text, color, scale);
        offset += 6 * scale;  // 5px width + 1px spacing, scaled
        text++;
    }
}

// SDL2 render function - replaces OpenGL/GLUT render
void render_sdl() {
    // 1. Check and swap double buffer
    if (buffer_swap_pending.exchange(false, std::memory_order_acquire)) {
        float* old_write = write_buffer.exchange(
            read_buffer.exchange(
                write_buffer.load(std::memory_order_relaxed),
                std::memory_order_relaxed
            ),
            std::memory_order_relaxed
        );
        (void)old_write;
    }
    
    // 2. Convert float RGB to SDL surface pixels (handle layout: x-major -> y-major)
    float* src_buf = read_buffer.load(std::memory_order_acquire);
    SDL_LockSurface(g_vga_surface);
    uint32_t* dst_pixels = (uint32_t*)g_vga_surface->pixels;
    
    for (int y = 0; y < ACTIVE_HEIGHT; y++) {
        for (int x = 0; x < ACTIVE_WIDTH; x++) {
            // Source buffer: x-major [x * HEIGHT + y]
            int src_idx = ((x * ACTIVE_HEIGHT) + y) * 3;
            // SDL surface: y-major [y * WIDTH + x]
            int dst_idx = y * ACTIVE_WIDTH + x;
            
            uint8_t r = (uint8_t)(src_buf[src_idx] * 255.0f);
            uint8_t g = (uint8_t)(src_buf[src_idx + 1] * 255.0f);
            uint8_t b = (uint8_t)(src_buf[src_idx + 2] * 255.0f);
            
            dst_pixels[dst_idx] = SDL_MapRGB(g_vga_surface->format, r, g, b);
        }
    }
    SDL_UnlockSurface(g_vga_surface);
    
    // 3. Clear screen background
    SDL_FillRect(g_screen_surface, NULL, 
        SDL_MapRGB(g_screen_surface->format, 25, 25, 25));
    
    // Calculate font scale based on window height (min scale = 2)
    int font_scale = g_window_height / 200;
    if (font_scale < 2) font_scale = 2;
    int font_height = 5 * font_scale;  // 5 rows * scale
    
    // 4. Calculate VGA display area (scale to fit, maintain 4:3 aspect ratio)
    // Leave space for: label (MARGIN_TOP) + VGA area + margin + LED area
    int vga_top = MARGIN_TOP + font_height + 5;  // VGA area starts below label
    int available_height = g_window_height - vga_top - LED_AREA_HEIGHT - MARGIN;
    int vga_display_w = g_window_width - MARGIN * 2;  // Available width (minus margins)
    int vga_display_h = vga_display_w * 3 / 4;        // Maintain 4:3 aspect ratio
    
    // If height exceeds available space, scale based on height instead
    if (vga_display_h > available_height) {
        vga_display_h = available_height;
        vga_display_w = vga_display_h * 4 / 3;
    }
    
    // Center the display
    SDL_Rect vga_rect = {
        (g_window_width - vga_display_w) / 2,
        vga_top,
        vga_display_w,
        vga_display_h
    };
    
    // 5. Scale and blit VGA area (single blit replaces 300k+ draw calls)
    SDL_BlitScaled(g_vga_surface, NULL, g_screen_surface, &vga_rect);
    
    // Draw VGA label (in the top margin area)
    uint32_t label_color = SDL_MapRGB(g_screen_surface->format, 200, 200, 200);
    draw_label(g_screen_surface, vga_rect.x, MARGIN_TOP, "VGA", label_color, font_scale);
    
    // 6. Draw LED area (below VGA display)
    int led_y_start = vga_rect.y + vga_rect.h + MARGIN;
    SDL_Rect led_bg = {0, led_y_start, g_window_width, LED_AREA_HEIGHT};
    SDL_FillRect(g_screen_surface, &led_bg,
        SDL_MapRGB(g_screen_surface->format, 50, 50, 50));
    
    // 7. Draw 5 LEDs
    const int led_spacing = g_window_width / 6;
    const int led_radius = 15;
    for (int i = 0; i < 5; i++) {
        int cx = led_spacing * (i + 1);
        int cy = led_y_start + LED_AREA_HEIGHT / 2;
        uint32_t color = (leds_state[i].load() == 0) ?
            SDL_MapRGB(g_screen_surface->format, 255, 0, 0) :
            SDL_MapRGB(g_screen_surface->format, 50, 0, 0);
        SDL_Rect led_rect = {cx - led_radius, cy - led_radius,
                            led_radius * 2, led_radius * 2};
        SDL_FillRect(g_screen_surface, &led_rect, color);
    }
    
    // Draw LED label (centered vertically in LED area)
    int led_label_y = led_y_start + (LED_AREA_HEIGHT - font_height) / 2;
    draw_label(g_screen_surface, 10, led_label_y, "LED", label_color, font_scale);
    
    // 8. Update window
    SDL_UpdateWindowSurface(g_window);
}

// handle up/down/left/right arrow keys
std::atomic<int> keys[5] = {{1}, {1}, {1}, {1}, {1}}; // 初始化为未激活状态

// SDL2 event loop - replaces GLUT callback-based event handling
void run_event_loop() {
    SDL_Event e;
    bool running = true;
    
    while (running && !g_quit_requested.load(std::memory_order_acquire)) {
        // Poll all events (non-blocking)
        while (SDL_PollEvent(&e)) {
            switch (e.type) {
                case SDL_QUIT:  // Window close button - works on all platforms
                    running = false;
                    break;
                    
                case SDL_KEYDOWN:
                    switch (e.key.keysym.sym) {
                        case SDLK_a:
                            keys[0].store(0, std::memory_order_release);
                            restart_triggered.store(true, std::memory_order_release);
                            break;
                        case SDLK_s: keys[1].store(0); break;
                        case SDLK_d: keys[2].store(0); break;
                        case SDLK_f: keys[3].store(0); break;
                        case SDLK_g: keys[4].store(0); break;
                        case SDLK_ESCAPE:
                        case SDLK_q:
                            running = false;
                            break;
                    }
                    break;
                    
                case SDL_KEYUP:
                    switch (e.key.keysym.sym) {
                        case SDLK_a: keys[0].store(1); break;
                        case SDLK_s: keys[1].store(1); break;
                        case SDLK_d: keys[2].store(1); break;
                        case SDLK_f: keys[3].store(1); break;
                        case SDLK_g: keys[4].store(1); break;
                    }
                    break;
            }
        }
        
        // Render frame
        render_sdl();
        SDL_Delay(16);  // ~60 FPS
    }
    
    g_quit_requested.store(true, std::memory_order_release);
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
    
    // SDL initialization completes synchronously in main thread
    // Add a short delay to ensure window is shown
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

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
    
    // 1. Initialize SDL (must be on main thread)
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        std::cerr << "SDL_Init failed: " << SDL_GetError() << std::endl;
        return 1;
    }
    
    // 2. Create window (add ALLOW_HIGHDPI for macOS Retina support)
    g_window = SDL_CreateWindow("VGA and LED Simulator (SDL2) - Press ESC or Q to exit",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        800, 600,
        SDL_WINDOW_SHOWN | SDL_WINDOW_ALLOW_HIGHDPI);
        
    if (!g_window) {
        std::cerr << "SDL_CreateWindow failed: " << SDL_GetError() << std::endl;
        SDL_Quit();
        return 1;
    }
    
    g_screen_surface = SDL_GetWindowSurface(g_window);
    
    // Get actual surface size (handle macOS Retina and other HiDPI screens)
    g_window_width = g_screen_surface->w;
    g_window_height = g_screen_surface->h;
    std::cout << "Window surface size: " << g_window_width << "x" << g_window_height << std::endl;
    
    // 3. Create VGA buffer surface (32-bit RGB888, cross-platform safe)
    g_vga_surface = SDL_CreateRGBSurfaceWithFormat(0, ACTIVE_WIDTH, ACTIVE_HEIGHT, 
        32, SDL_PIXELFORMAT_RGB888);
    if (!g_vga_surface) {
        std::cerr << "Failed to create VGA surface: " << SDL_GetError() << std::endl;
        SDL_DestroyWindow(g_window);
        SDL_Quit();
        return 1;
    }
    
    // 4. Start simulation thread (after SDL initialization)
    g_sim_thread = std::thread(simulation_loop);

    // 5. Run event loop (main thread)
    run_event_loop();

    // 6. Cleanup (unified path, no platform checks needed)
    cleanup_simulation();
    
    return 0;
}
