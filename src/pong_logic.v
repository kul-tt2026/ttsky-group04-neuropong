module pong (clk, reset, l_paddle_up, l_paddle_down, r_paddle_up, r_paddle_down, l_paddle_y, r_paddle_y, ball_x, ball_y, l_score, r_score);
    input wire clk;
    input wire reset;

    input wire l_paddle_up;
    input wire l_paddle_down;

    input wire r_paddle_up;
    input wire r_paddle_down;

    output reg [9:0] l_paddle_y;
    output reg [9:0] r_paddle_y;

    output reg [9:0] ball_x;
    output reg [9:0] ball_y;

    output reg [3:0] l_score;
    output reg [3:0] r_score;

    parameter V_DISPLAY = 480;
    parameter H_DISPLAY = 640;

    parameter X = 15;
    parameter L_PADDLE_X = 2*X;
    parameter R_PADDLE_X = H_DISPLAY - 3*X;
    parameter PADDLE_HEIGHT = 5*X;

    parameter BALL_SPEED = 1;
    parameter PADDLE_SPEED = 1;

    reg ball_dir_x = 0; // 1 => to left, 0 => to right
    reg ball_dir_y = 0; // 1 => to top, 0 => to bottom


    always @(posedge clk) begin

        if (reset) begin
            l_paddle_y <= V_DISPLAY/2;
            r_paddle_y <= V_DISPLAY/2;

            ball_x <= H_DISPLAY/2;
            ball_y <= V_DISPLAY/2;

            ball_dir_x <= 0;
            ball_dir_y <= 0;

            l_score <= 4'd0;
            r_score <= 4'd0;

        end else begin

            // ball position update
            if (ball_dir_x == 0) begin
                ball_x <= ball_x + BALL_SPEED;
            end else begin
                ball_x <= ball_x - BALL_SPEED;
            end

            if (ball_dir_y == 0) begin
                ball_y <= ball_y + BALL_SPEED;
            end else begin
                ball_y <= ball_y - BALL_SPEED;
            end

            // top border collision
            if (ball_y <= BALL_SPEED) begin
                ball_dir_y <= 0;
            // bottom border collision
            end else if (ball_y + X + BALL_SPEED >= V_DISPLAY) begin
                ball_dir_y <= 1;
            end 

            // left border collision
            if (ball_x <= BALL_SPEED) begin        
                ball_dir_x <= 0;

                l_paddle_y <= V_DISPLAY/2;
                r_paddle_y <= V_DISPLAY/2;

                ball_x <= H_DISPLAY/2;
                ball_y <= V_DISPLAY/2;

                if (r_score == 4'd9) begin
                    l_score <= 4'd0;
                    r_score <= 4'd0;
                end else begin
                    r_score <= r_score + 1;
                end

            // right border collision
            end else if (ball_x + X + BALL_SPEED >= H_DISPLAY) begin
                ball_dir_x <= 1;

                l_paddle_y <= V_DISPLAY/2;
                r_paddle_y <= V_DISPLAY/2;

                ball_x <= H_DISPLAY/2;
                ball_y <= V_DISPLAY/2;

                if (l_score == 4'd9) begin
                    l_score <= 4'd0;
                    r_score <= 4'd0;
                end else begin
                    l_score <= l_score + 1;
                end

            // left paddle collision
            end else if (ball_x == L_PADDLE_X + X && (ball_y + X >= l_paddle_y && ball_y < l_paddle_y + PADDLE_HEIGHT))  begin
                    ball_dir_x <= 0;
            // right paddle collision
            end else if (ball_x == R_PADDLE_X && (ball_y + X >= r_paddle_y && ball_y < r_paddle_y + PADDLE_HEIGHT)) begin
                ball_dir_x <= 1;
            end
        end
    end
endmodule