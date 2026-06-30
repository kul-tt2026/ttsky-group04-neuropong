module render(clk, reset, h_count, v_count, draw_enable, l_paddle_y, r_paddle_y, ball_x, ball_y, red, green, blue);

    // IO
    input wire clk;
    input wire reset;

    input wire [9:0] h_count;
    input wire [9:0] v_count;
    input wire draw_enable;

    input wire [9:0] l_paddle_y;
    input wire [9:0] r_paddle_y;
    input wire [9:0] ball_x;        //position of top left corner
    input wire [9:0] ball_y;

    output reg [1:0] red;
    output reg [1:0] green;
    output reg [1:0] blue;

    parameter H_DISPLAY = 640;

    parameter X = 15;
    parameter L_PADDLE_X = 2*X;
    parameter R_PADDLE_X = H_DISPLAY - 3*X;

    wire ball_in = (h_count >= ball_x && h_count < ball_x + X) && (v_count >= ball_y && v_count < ball_y + X);
    wire l_paddle_in = (h_count >= L_PADDLE_X && h_count < L_PADDLE_X + X) && (v_count >= l_paddle_y && v_count < l_paddle_y + 5*X);
    wire r_paddle_in = (h_count >= R_PADDLE_X && h_count < R_PADDLE_X + X) && (v_count >= r_paddle_y && v_count < r_paddle_y + 5*X);


    
    always @(posedge clk) begin
        if (reset) begin
            red <= 2'b00;
            green <= 2'b00;
            blue <= 2'b00;

        end else begin
            if (draw_enable) begin
                // ball
                if (ball_in) begin
                    red <= 2'b11;
                    green <= 2'b11;
                    blue <= 2'b11;
                // left paddle
                end else if (l_paddle_in) begin
                    red <= 2'b11;
                    green <= 2'b00;
                    blue <= 2'b00;
                // right paddle
                end else if (r_paddle_in) begin
                    red <= 2'b00;
                    green <= 2'b00;
                    blue <= 2'b11;
                // background
                end else begin
                    red <= 2'b00;
                    green <= 2'b00;
                    blue <= 2'b00;
                end
            end else begin
                red <= 2'b00;
                green <= 2'b00;
                blue <= 2'b00;
            end
        end
    end


endmodule