`timescale 1ns / 1ns

module vga_pic(
input wire vga_clk , //VGA working clock, 25MHz
input wire sys_rst_n , //Reset signal. Low level is effective
input wire [9:0] pix_x , //X coordinate of current pixel
input wire [9:0] pix_y , //Y coordinate of current pixel
input wire up,
input wire down,
input wire left,
input wire right,


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
reg up_prev = 1;            // store button state in previous clock
wire up_falling_edge;       // detect button edge

always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        up_prev <= 1;
    end else begin
        up_prev <= up;
    end
end

// detect the negedge
assign up_falling_edge = (up_prev == 1 && up == 0);

// detect edge of button
reg down_prev = 1;            // store button state in previous clock
wire down_falling_edge;       // detect button edge

always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        down_prev <= 1;
    end else begin
        down_prev <= down;
    end
end

// detect the negedge
assign down_falling_edge = (down_prev == 1 && down == 0);

// detect edge of button
reg left_prev = 1;            // store button state in previous clock
wire left_falling_edge;       // detect button edge

always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        left_prev <= 1;
    end else begin
        left_prev <= left;
    end
end

// detect the negedge
assign left_falling_edge = (left_prev == 1 && left == 0);

// detect edge of button
reg right_prev = 1;            // store button state in previous clock
wire right_falling_edge;       // detect button edge

always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        right_prev <= 1;
    end else begin
        right_prev <= right;
    end
end

// detect the negedge
assign right_falling_edge = (right_prev == 1 && right == 0);


// move circle
always @(posedge vga_clk or negedge sys_rst_n) begin
    if (!sys_rst_n) begin
        // reset
        ball_x <= 320;
        ball_y <= 240;
    end 
    else begin
        // negedge of button -> circle move
        //if (!button) begin
		  if (up_falling_edge) 
            if (ball_y > BALL_RADIUS)
                ball_y <= ball_y - 10;
		
          if (down_falling_edge)
            if (ball_y  < V_VALID - BALL_RADIUS)
                ball_y <= ball_y + 10;

          if (left_falling_edge)
            if (ball_x > BALL_RADIUS)
                ball_x <= ball_x - 10;
        
		  if (right_falling_edge)
            if (ball_x < H_VALID - BALL_RADIUS)
                ball_x <= ball_x + 10;
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