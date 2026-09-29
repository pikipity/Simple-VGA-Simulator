// simulator.cpp - Headless simulation host for the virtual development board (v2)
//
// Wraps the Verilated VDevelopmentBoard model (fixed v2 ports). Samples the
// VGA output stream and emits one binary frame per v_sync rising edge on
// stdout; receives button / ideal-input / quit commands on stdin via a
// reader thread. All logs go to stderr; stdout carries binary frames only.
//
// Frame format (little-endian), 12-byte header + payload:
//   [u32 magic = 0x31474156 "VGA1"][u32 frame_no][u8 led_bits][u8 flags][u16 reserved]
//   [payload: 640*480*2 bytes RGB565, y-major]
//   led_bits: bit i = led[i] lit (active-low resolved: pin 0 -> bit 1)
//   flags:    bit0 = ideal input enabled
//
// stdin commands:
//   'B' [u8 id 0..4 = SW1..SW5] [u8 state: 0 = pressed, 1 = released]
//   'I' [u8 0|1]   ideal input (1 = no bounce injection)
//   'Q'            quit (stdin EOF also quits)

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>
#include <algorithm>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
static int read_fd(int fd, void* buf, unsigned n) { return _read(fd, buf, n); }
#else
#include <unistd.h>
static int read_fd(int fd, void* buf, unsigned n) { return ::read(fd, buf, n); }
#endif

#include "VDevelopmentBoard.h"
#include "verilated.h"

// ---------- VGA timing: 640x480 @ 60Hz, 25MHz pixel clock ----------
static const int ACTIVE_WIDTH   = 640;
static const int ACTIVE_HEIGHT  = 480;
static const int TOTAL_WIDTH    = 800;
static const int TOTAL_HEIGHT   = 525;
static const int H_ACTIVE_START = 144;  // H_SYNC(96) + H_BACK(40) + H_LEFT(8)
static const int V_ACTIVE_START = 35;   // V_SYNC(2) + V_BACK(25) + V_TOP(8)

static const int NUM_BUTTONS = 5;       // SW1..SW5 -> key_reset, key[0..3]

// ---------- wire protocol ----------
static const uint32_t FRAME_MAGIC   = 0x31474156;  // 'VGA1'
static const size_t   FRAME_PAYLOAD = (size_t)ACTIVE_WIDTH * ACTIVE_HEIGHT * 2;
static const auto     FRAME_PERIOD  = std::chrono::nanoseconds(16666667);  // wall-clock 60Hz

// ---------- shared state (stdin reader thread -> sim thread) ----------
struct ButtonEvent {
    uint8_t id;     // 0..4 = SW1..SW5; 0xFF = settle-all (ideal input turned on)
    uint8_t state;  // 0 = pressed, 1 = released
};

static std::mutex              g_cmd_mutex;
static std::queue<ButtonEvent> g_button_events;
static std::atomic<int>        g_pending_events{0};
static std::atomic<bool>       g_ideal_input{false};
static std::atomic<bool>       g_quit{false};

// ---------- sim-thread-only input/bounce state ----------
struct ScheduledLevel {
    uint64_t due_cycle;  // 50MHz clock cycle at which to apply
    uint8_t  button;
    uint8_t  level;
};
static std::vector<ScheduledLevel> g_schedule;
static uint8_t  g_pin_level[NUM_BUTTONS]  = {1, 1, 1, 1, 1};  // driven to model
static uint8_t  g_pin_target[NUM_BUTTONS] = {1, 1, 1, 1, 1};  // settled value
static uint32_t g_rng_state = 0x1CEB00DAu;

static uint32_t xorshift32() {
    uint32_t x = g_rng_state;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    g_rng_state = x ? x : 0x9E3779B9u;
    return g_rng_state;
}

// Bounce injection: residual bounce of real hardware debounce (4.7K pull-up +
// 0.1uF cap) is sub-ms..2ms. Before settling to the target level, toggle the
// pin 2..6 times with random gaps in [0.1ms, 2ms] (= 5000..100000 cycles @50MHz).
static void start_button_event(uint8_t id, uint8_t state, uint64_t now_cycle) {
    g_schedule.erase(std::remove_if(g_schedule.begin(), g_schedule.end(),
        [id](const ScheduledLevel& s) { return s.button == id; }),
        g_schedule.end());
    g_pin_target[id] = state;

    if (g_ideal_input.load(std::memory_order_acquire)) {
        g_pin_level[id] = state;  // ideal: settle immediately
        return;
    }

    g_rng_state ^= (uint32_t)(now_cycle * 2654435761u) ^ ((uint32_t)id * 97u + state);
    if (!g_rng_state) g_rng_state = 0x9E3779B9u;

    int flips = 2 + (int)(xorshift32() % 5);  // 2..6 flips
    uint8_t  level = g_pin_level[id];
    uint64_t due   = now_cycle;
    for (int i = 0; i < flips; i++) {
        level ^= 1;
        due += 5000 + xorshift32() % 95001;
        g_schedule.push_back({due, id, level});
    }
    if (level != state) {
        due += 5000 + xorshift32() % 95001;
        g_schedule.push_back({due, id, state});
    }
}

static void apply_due_levels(uint64_t now_cycle) {
    for (auto it = g_schedule.begin(); it != g_schedule.end();) {
        if (it->due_cycle <= now_cycle) {
            g_pin_level[it->button] = it->level;
            it = g_schedule.erase(it);
        } else {
            ++it;
        }
    }
}

static void process_commands(uint64_t now_cycle) {
    if (g_pending_events.load(std::memory_order_acquire) == 0) return;
    std::lock_guard<std::mutex> lock(g_cmd_mutex);
    while (!g_button_events.empty()) {
        ButtonEvent ev = g_button_events.front();
        g_button_events.pop();
        g_pending_events.fetch_sub(1, std::memory_order_release);
        if (ev.id == 0xFF) {  // ideal input turned on: drop bounce, settle now
            g_schedule.clear();
            for (int i = 0; i < NUM_BUTTONS; i++) g_pin_level[i] = g_pin_target[i];
        } else {
            start_button_event(ev.id, ev.state, now_cycle);
        }
    }
}

// ---------- stdin reader thread ----------
static bool read_exact_fd(void* buf, size_t n) {
    uint8_t* p = (uint8_t*)buf;
    while (n > 0) {
        int r = read_fd(0, p, (unsigned)n);
        if (r <= 0) return false;  // EOF or error
        p += r; n -= (size_t)r;
    }
    return true;
}

static void stdin_reader() {
    for (;;) {
        uint8_t cmd;
        if (!read_exact_fd(&cmd, 1)) break;  // EOF -> quit
        switch (cmd) {
            case 'B': {
                uint8_t args[2];
                if (!read_exact_fd(args, 2)) { g_quit.store(true); return; }
                if (args[0] < NUM_BUTTONS && args[1] <= 1) {
                    std::lock_guard<std::mutex> lock(g_cmd_mutex);
                    g_button_events.push({args[0], args[1]});
                    g_pending_events.fetch_add(1, std::memory_order_release);
                }
                break;
            }
            case 'I': {
                uint8_t v;
                if (!read_exact_fd(&v, 1)) { g_quit.store(true); return; }
                bool ideal = (v != 0);
                bool was   = g_ideal_input.exchange(ideal, std::memory_order_acq_rel);
                if (ideal && !was) {  // settle in-flight bounce immediately
                    std::lock_guard<std::mutex> lock(g_cmd_mutex);
                    g_button_events.push({0xFF, 0});
                    g_pending_events.fetch_add(1, std::memory_order_release);
                }
                break;
            }
            case 'Q':
                g_quit.store(true, std::memory_order_release);
                return;
            default:
                break;  // ignore unknown bytes
        }
    }
    g_quit.store(true, std::memory_order_release);
}

// ---------- model ----------
static VDevelopmentBoard* display;
static uint64_t main_time = 0;
double sc_time_stamp() { return main_time; }  // called by $time in Verilog

static void apply_inputs() {
    display->key_reset = g_pin_level[0];
    display->key = (uint8_t)(g_pin_level[1]
                           | (g_pin_level[2] << 1)
                           | (g_pin_level[3] << 2)
                           | (g_pin_level[4] << 3));
}

// simulate a single full clock cycle (rise + fall)
static void tick() {
    main_time++;
    display->clk = 1;
    apply_inputs();
    display->eval();

    main_time++;
    display->clk = 0;
    apply_inputs();
    display->eval();
}

// ---------- frame buffers: write buffer + send buffer, swapped at frame edge ----------
static uint16_t  g_framebuf_a[ACTIVE_WIDTH * ACTIVE_HEIGHT] = {};
static uint16_t  g_framebuf_b[ACTIVE_WIDTH * ACTIVE_HEIGHT] = {};
static uint16_t* g_write_buf = g_framebuf_a;
static uint16_t* g_send_buf  = g_framebuf_b;

// tracking VGA signals
static int  coord_x   = 0;
static int  coord_y   = 0;
static bool pre_h_sync = false;
static bool pre_v_sync = false;

static uint32_t g_frame_no = 0;

static void send_frame() {
    uint8_t header[12];
    header[0] = (uint8_t)(FRAME_MAGIC & 0xFF);
    header[1] = (uint8_t)((FRAME_MAGIC >> 8) & 0xFF);
    header[2] = (uint8_t)((FRAME_MAGIC >> 16) & 0xFF);
    header[3] = (uint8_t)((FRAME_MAGIC >> 24) & 0xFF);
    header[4] = (uint8_t)(g_frame_no & 0xFF);
    header[5] = (uint8_t)((g_frame_no >> 8) & 0xFF);
    header[6] = (uint8_t)((g_frame_no >> 16) & 0xFF);
    header[7] = (uint8_t)((g_frame_no >> 24) & 0xFF);
    header[8] = (uint8_t)((~display->led) & 0x0F);  // active-low -> lit bits
    header[9] = g_ideal_input.load(std::memory_order_acquire) ? 1 : 0;
    header[10] = 0;
    header[11] = 0;

    // payload is u16 RGB565 little-endian (all target hosts are LE)
    fwrite(header, 1, sizeof(header), stdout);
    fwrite(g_send_buf, 2, ACTIVE_WIDTH * ACTIVE_HEIGHT, stdout);
    fflush(stdout);
}

// wall-clock 60Hz pacing: real hardware is real-time; sleep up to the next
// 16.667ms boundary after each frame, run free if sim is slower than real-time
static void pace_frame() {
    static auto last = std::chrono::steady_clock::now() - FRAME_PERIOD;
    auto target = last + FRAME_PERIOD;
    auto now    = std::chrono::steady_clock::now();
    if (now < target) {
        std::this_thread::sleep_until(target);
        last = target;
    } else {
        last = now;
    }
}

// read VGA outputs and update the write buffer
static void sample_pixel() {
    coord_x = (coord_x + 1) % TOTAL_WIDTH;

    if (display->vga_hs && !pre_h_sync) {  // positive edge of h_sync
        coord_x = 0;
        coord_y = (coord_y + 1) % TOTAL_HEIGHT;
    }

    if (display->vga_vs && !pre_v_sync) {  // positive edge of v_sync: frame done
        coord_y = 0;
        uint16_t* tmp = g_send_buf;
        g_send_buf  = g_write_buf;
        g_write_buf = tmp;
        g_frame_no++;
        send_frame();
        pace_frame();
        if (g_frame_no % 600 == 0) {
            std::cerr << "[Sim] frame " << g_frame_no << "\n";
        }
    }

    if (coord_x >= H_ACTIVE_START && coord_x < H_ACTIVE_START + ACTIVE_WIDTH &&
        coord_y >= V_ACTIVE_START && coord_y < V_ACTIVE_START + ACTIVE_HEIGHT) {
        int x = coord_x - H_ACTIVE_START;
        int y = coord_y - V_ACTIVE_START;
        g_write_buf[y * ACTIVE_WIDTH + x] = display->vga_d;
    }

    pre_h_sync = display->vga_hs;
    pre_v_sync = display->vga_vs;
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);

#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY);  // stdout carries raw binary frames
    _setmode(_fileno(stdin), _O_BINARY);
#endif

    std::thread input_thread(stdin_reader);
    input_thread.detach();  // blocked in read(); dies with the process

    display = new VDevelopmentBoard;

    // power-on: all buttons released (active-high idle), zero-state eval
    display->clk = 0;
    apply_inputs();
    display->eval();

    std::cerr << "SIM_READY\n";

    uint64_t cycle = 0;  // 50MHz clock cycles elapsed
    while (!Verilated::gotFinish() && !g_quit.load(std::memory_order_acquire)) {
        process_commands(cycle);
        apply_due_levels(cycle);
        tick();
        tick();
        sample_pixel();  // 2 full clocks per sample -> 25MHz pixel clock
        cycle += 2;
    }

    std::cerr << "[Sim] quit after " << g_frame_no << " frames, "
              << cycle << " clocks\n";
    display->final();
    delete display;
    return 0;
}
