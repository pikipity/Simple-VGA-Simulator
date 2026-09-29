module top(
    input  wire        clk,
    input  wire        rst_n,
    input  wire [1:0]  key,
    output wire [1:0]  led,
    output wire        hsync,
    output wire        vsync,
    output wire [15:0] rgb
);

wire [7:0] cnt;

counter u_cnt (
    .clk   (clk),
    .rst_n (rst_n),
    .q     (cnt)
);

assign led   = cnt[1:0] ^ {2{key[0]}};
assign hsync = cnt[7];
assign vsync = cnt[6];
assign rgb   = {5'd0, cnt, 3'b101};

endmodule
