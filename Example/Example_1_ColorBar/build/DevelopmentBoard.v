`timescale 1ns / 1ns
// ============================================================
// DevelopmentBoard.v  —  虚拟开发板 PCB 走线（自动生成，请勿手改）
//
// 本文件由构建管线按工程 .qsf 约束生成：
//   学生顶层端口 -> FPGA 引脚 -> 板卡外设
// 板卡: EP4CE10_Pro (Cyclone IV E EP4CE10F17C8N)
// ============================================================
module DevelopmentBoard(
    input  wire        clk,        // Y7 50MHz 晶振,        PIN_E1
    input  wire        key_reset,  // SW1 (RESET),          PIN_M15, 按下=0
    input  wire [3:0]  key,        // SW2~SW5 (KEY1~KEY4),  PIN_M2/M1/E15/E16, 按下=0
    output wire [3:0]  led,        // LED2~LED5,            PIN_L7/M6/P3/N3, 0=亮
    output wire        vga_hs,     // VGA_HSYNC,            PIN_C2
    output wire        vga_vs,     // VGA_VSYNC,            PIN_D1
    output wire [15:0] vga_d       // VGA_D[15:0], RGB565
);

ColorBar u_top (
    .sys_clk(clk),
    .sys_rst_n(key_reset),
    .hsync(vga_hs),
    .vsync(vga_vs),
    .rgb({vga_d[15], vga_d[14], vga_d[13], vga_d[12], vga_d[11], vga_d[10], vga_d[9], vga_d[8], vga_d[7], vga_d[6], vga_d[5], vga_d[4], vga_d[3], vga_d[2], vga_d[1], vga_d[0]})
);

endmodule
