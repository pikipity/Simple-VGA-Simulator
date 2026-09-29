// mini_top.v - minimal v2-style student top level for protocol testing
// 25MHz pixel clock from 50MHz input, 640x480@60 VGA timing, 8 color bars,
// LEDs follow the buttons (both active-low), key_reset is the async reset.
module mini_top(
    input  wire        clk_50m,
    input  wire        rst_n,
    input  wire [3:0]  btn,
    output wire [3:0]  led_out,
    output wire        hsync,
    output wire        vsync,
    output wire [15:0] rgb
);
    // 50MHz -> 25MHz pixel clock
    reg clk_25m = 1'b0;
    always @(posedge clk_50m or negedge rst_n) begin
        if (!rst_n) clk_25m <= 1'b0;
        else        clk_25m <= ~clk_25m;
    end

    // 640x480@60 timing (25MHz pixel clock)
    localparam H_SYNC = 96, H_BACK = 40, H_LEFT = 8, H_ACTIVE = 640;
    localparam H_RIGHT = 8, H_FRONT = 8;
    localparam H_TOTAL = H_SYNC + H_BACK + H_LEFT + H_ACTIVE + H_RIGHT + H_FRONT; // 800
    localparam V_SYNC = 2, V_BACK = 25, V_TOP = 8, V_ACTIVE = 480;
    localparam V_BOTTOM = 8, V_FRONT = 2;
    localparam V_TOTAL = V_SYNC + V_BACK + V_TOP + V_ACTIVE + V_BOTTOM + V_FRONT; // 525

    reg [9:0] hcnt = 10'd0;
    reg [9:0] vcnt = 10'd0;
    always @(posedge clk_25m or negedge rst_n) begin
        if (!rst_n) begin
            hcnt <= 10'd0;
            vcnt <= 10'd0;
        end else if (hcnt == H_TOTAL - 1) begin
            hcnt <= 10'd0;
            if (vcnt == V_TOTAL - 1) vcnt <= 10'd0;
            else                     vcnt <= vcnt + 10'd1;
        end else begin
            hcnt <= hcnt + 10'd1;
        end
    end

    // sync pulses high-active, rising edge at counter 0
    assign hsync = (hcnt < H_SYNC);
    assign vsync = (vcnt < V_SYNC);

    wire active = (hcnt >= H_SYNC + H_BACK + H_LEFT) &&
                  (hcnt <  H_SYNC + H_BACK + H_LEFT + H_ACTIVE) &&
                  (vcnt >= V_SYNC + V_BACK + V_TOP) &&
                  (vcnt <  V_SYNC + V_BACK + V_TOP + V_ACTIVE);

    // 8 vertical color bars, 128px each (RGB565)
    wire [9:0] pix_x = hcnt - (H_SYNC + H_BACK + H_LEFT);
    reg [15:0] bar_color;
    always @(*) begin
        case (pix_x[9:7])
            3'd0:    bar_color = 16'hFFFF;  // white
            3'd1:    bar_color = 16'hFFE0;  // yellow
            3'd2:    bar_color = 16'h07FF;  // cyan
            3'd3:    bar_color = 16'h07E0;  // green
            3'd4:    bar_color = 16'hF81F;  // magenta
            3'd5:    bar_color = 16'hF800;  // red
            3'd6:    bar_color = 16'h001F;  // blue
            default: bar_color = 16'h0000;  // black
        endcase
    end

    assign rgb     = active ? bar_color : 16'h0000;
    assign led_out = btn;  // LEDs follow buttons (both active-low)
endmodule
