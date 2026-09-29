// DevelopmentBoard.v - hand-written fixture mirroring the generated wrapper
// (backend generates this from DevelopmentBoard.v.tpl + QSF pin mapping)
module DevelopmentBoard(
    input  wire        clk,        // Y7 50MHz
    input  wire        key_reset,  // SW1, pressed = 0
    input  wire [3:0]  key,        // SW2~SW5, pressed = 0
    output wire [3:0]  led,        // LED2~LED5, 0 = lit
    output wire        vga_hs,
    output wire        vga_vs,
    output wire [15:0] vga_d       // RGB565
);

    mini_top u_top(
        .clk_50m (clk),
        .rst_n   (key_reset),
        .btn     (key),
        .led_out (led),
        .hsync   (vga_hs),
        .vsync   (vga_vs),
        .rgb     (vga_d)
    );

endmodule
