// Test stand-in for sim/simulator.cpp (which is developed in parallel).
// A real Verilator harness: drives the DevelopmentBoard model, prints
// SIM_READY on stderr, streams wire-protocol frames on stdout at ~60 Hz,
// and answers stdin commands 'B' / 'I' / 'Q'.
#include "VDevelopmentBoard.h"
#include "verilated.h"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <unistd.h>

static std::atomic<bool> g_quit(false);
static const uint32_t MAGIC = 0x31474156;  // 'VGA1'
static uint8_t g_payload[640 * 480 * 2];

static void stdin_reader(VDevelopmentBoard* top) {
    uint8_t c;
    while (!g_quit.load()) {
        ssize_t n = ::read(0, &c, 1);
        if (n <= 0) break;
        if (c == 'B') {
            uint8_t id, state;
            if (::read(0, &id, 1) != 1) break;
            if (::read(0, &state, 1) != 1) break;
            bool pressed = (state == 0);
            if (id == 0) {
                top->key_reset = pressed ? 0 : 1;
            } else if (id >= 1 && id <= 4) {
                uint8_t key = top->key;
                if (pressed) key &= ~(1u << (id - 1));
                else key |= (1u << (id - 1));
                top->key = key;
            }
        } else if (c == 'I') {
            uint8_t on;
            if (::read(0, &on, 1) != 1) break;
        } else if (c == 'Q') {
            g_quit.store(true);
            return;
        }
    }
    g_quit.store(true);
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    VDevelopmentBoard* top = new VDevelopmentBoard;
    top->clk = 0;
    top->key_reset = 1;
    top->key = 0xF;
    top->eval();

    fprintf(stderr, "SIM_READY\n");
    fflush(stderr);

    std::thread reader(stdin_reader, top);

    uint32_t frame_no = 0;
    while (!g_quit.load()) {
        for (int i = 0; i < 200 && !g_quit.load(); i++) {
            top->clk = !top->clk;
            top->eval();
        }
        frame_no++;
        uint8_t leds = 0;
        for (int i = 0; i < 4; i++) {
            if (!((top->led >> i) & 1)) leds |= (1u << i);  // active low
        }
        uint8_t header[12];
        header[0] = MAGIC & 0xFF;
        header[1] = (MAGIC >> 8) & 0xFF;
        header[2] = (MAGIC >> 16) & 0xFF;
        header[3] = (MAGIC >> 24) & 0xFF;
        header[4] = frame_no & 0xFF;
        header[5] = (frame_no >> 8) & 0xFF;
        header[6] = (frame_no >> 16) & 0xFF;
        header[7] = (frame_no >> 24) & 0xFF;
        header[8] = leds;
        header[9] = 0;
        header[10] = 0;
        header[11] = 0;
        // Cheap moving pattern so frames differ.
        g_payload[(frame_no * 977) % sizeof(g_payload)] = frame_no & 0xFF;
        ::write(1, header, sizeof(header));
        ::write(1, g_payload, sizeof(g_payload));
        std::this_thread::sleep_for(std::chrono::milliseconds(16));
    }

    reader.join();
    top->final();
    delete top;
    return 0;
}
