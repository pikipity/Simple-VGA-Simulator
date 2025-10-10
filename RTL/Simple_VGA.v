`timescale 1ns / 1ns

module Simple_VGA(
input wire sys_clk , //System Clock, 50MHz
input wire sys_rst_n , //Reset signal. Low level is effective
input wire up,
input wire down,
input wire left,
input wire right,

output wire hsync , //Line sync signal
output wire vsync , //Field sync signal
output wire [15:0] rgb //RGB565 color data

);

 ////
 //\* Parameter and Internal Signal \//
 ////

 //wire define
 //wire vga_clk ; //VGA working clock, 25MHz
 //wire locked ; //PLL locked signal
 //wire rst_n ; //VGA reset signal
 wire [9:0] pix_x ; //x coordinate of current pixel
 wire [9:0] pix_y ; //y coordinate of current pixel
 wire [15:0] pix_data; //color information
 
 reg vga_clk;
always @(posedge sys_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        vga_clk <= 0;
    end else begin
        vga_clk <= ~vga_clk;
    end
end

// //VGA reset signal.
// // When the system reset signal and the PLL locked signal are both in high level, the system works. 
// assign rst_n = (sys_rst_n & locked);
//
// ////
// //\* Instantiation \//
// ////
//
// //------------- clk_gen_inst -------------
// pll_ip clk_gen_inst
// (
// .areset (~sys_rst_n ), //Reset signal of PLL
// .inclk0 (sys_clk ), //Input clock of PLL, 50MHz
//
// .c0 (vga_clk ), //Output clock signal of PLL, 25MHz
// .locked (locked ) //PLL locked signal
// );

 //------------- vga_ctrl_inst -------------
 vga_ctrl vga_ctrl_inst
 (
 .vga_clk (vga_clk ), //VGA working clock, 25MHz
 .sys_rst_n (sys_rst_n ), //Reset signal. Low level is effective
 .pix_data (pix_data ), //color information

 .pix_x (pix_x ), //x coordinate of current pixel
 .pix_y (pix_y ), //y coordinate of current pixel
 .hsync (hsync ), //Line sync signal
 .vsync (vsync ), //Field sync signal
 .rgb (rgb ) //RGB565 color data
 );

 //------------- vga_pic_inst -------------
 vga_pic vga_pic_inst
 (
 .vga_clk (vga_clk ), //VGA working clock, 25MHz
 .sys_rst_n (sys_rst_n ), //Reset signal. Low level is effective
 .pix_x (pix_x ), //x coordinate of current pixel
 .pix_y (pix_y ), //y coordinate of current pixel
 .up(up),
 .down(down),
 .left(left),
 .right(right),

 .pix_data (pix_data ) //color information

 );

 endmodule