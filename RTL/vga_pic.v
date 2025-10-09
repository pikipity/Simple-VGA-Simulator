`timescale 1ns / 1ns

module vga_pic(
input wire vga_clk , //VGA working clock, 25MHz
input wire sys_rst_n , //Reset signal. Low level is effective
input wire [9:0] pix_x , //X coordinate of current pixel
input wire [9:0] pix_y , //Y coordinate of current pixel
input wire button,

output reg [15:0] pix_data //Color information

);

 ////
 //\* Parameter and Internal Signal \//
 ////
 //parameter define
 parameter H_VALID = 10'd640 , //Maximum x value
 V_VALID = 10'd480 ; //Maximum y value

 parameter RED = 16'hF800, //RED
 ORANGE = 16'hFC00, //Orange
 YELLOW = 16'hFFE0, //Yellow
 GREEN = 16'h07E0, //Green
 CYAN = 16'h07FF, //Cyan
 BLUE = 16'h001F, //Blue
 PURPPLE = 16'hF81F, //Purple
 BLACK = 16'h0000, //Black
 WHITE = 16'hFFFF, //White
 GRAY = 16'hD69A; //Grey

// parameters
reg [9:0] ball_x = 320;         // x corrdinate
reg [9:0] ball_y = 240;         // y coordinate
parameter BALL_RADIUS = 20;     // radius
parameter BALL_COLOR = BLUE; 
parameter BACKGROUND_COLOR = PURPPLE; 

// detect edge of button
reg button_prev = 1;            // store button state in previous clock
wire button_falling_edge;       // detect button edge

always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        button_prev <= 1;
    end else begin
        button_prev <= button;
    end
end

// detect the negedge
assign button_falling_edge = (button_prev == 1 && button == 0);


// move circle
always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        // reset
        ball_x <= 320;
        ball_y <= 240;
    end else begin
        // negedge of button -> circle move
        //if (!button) begin
		  if (button_falling_edge) begin
            if (ball_x > BALL_RADIUS) begin
                ball_x <= ball_x - 10;
            end
				else
					ball_x <= 320;
        end
		  
    end
end

// generate color
always @(*) begin
    if ((pix_x - ball_x) * (pix_x - ball_x) + (pix_y - ball_y) * (pix_y - ball_y) <= BALL_RADIUS * BALL_RADIUS) begin
        pix_data = BALL_COLOR; 
    end else begin
        pix_data = BACKGROUND_COLOR; 
    end
end
	 
	 

 endmodule