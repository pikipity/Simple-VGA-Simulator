`timescale 1ns / 1ns

module DevelopmentBoard(
    input wire clk, //50MHz
    input wire reset, B2, B3, B4, B5,
	 // reset is "a"
	 // B2 is "s"
	 // B3 is "d"
	 // B4 is "f"
	 // B5 is "g"
    output wire h_sync, v_sync,
    output wire [15:0] rgb
);

	// instance your model
	Simple_VGA Simple_VGA_inst(
		.sys_clk(clk),
		.sys_rst_n(reset),
		.hsync(h_sync),
		.vsync(v_sync),
		.rgb(rgb),
		.button(B2)
	);
    


endmodule
