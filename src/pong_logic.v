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

    wire [9:0] next_y_up = ball_y - BALL_SPEED;         // what next ball_y would be without boundries
    wire [9:0] next_y_down = ball_y + X + BALL_SPEED;

    wire top_hit = (ball_y <= BALL_SPEED) && (ball_dir_y == 1);
    wire bottom_hit = (next_y_down >= V_DISPLAY) && (ball_dir_y == 0);

    wire l_paddle_hit = ball_dir_x == 1 && (ball_x <= L_PADDLE_X + X + BALL_SPEED && ball_x + X >= L_PADDLE_X) && (ball_y + X >= l_paddle_y && ball_y < l_paddle_y + PADDLE_HEIGHT);
    wire r_paddle_hit = ball_dir_x == 0 && (ball_x <= R_PADDLE_X + X && ball_x + X + BALL_SPEED >= R_PADDLE_X) && (ball_y + X >= r_paddle_y && ball_y < r_paddle_y + PADDLE_HEIGHT);


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

            // top border collision
            if (top_hit) begin
                ball_dir_y <= 0;
                ball_y <= BALL_SPEED - ball_y;      // rebounce of border

            // bottom border collision
            end else if (bottom_hit) begin
                ball_dir_y <= 1;
                ball_y <= (V_DISPLAY - X) - (next_y_down - V_DISPLAY);
            
            // NO top/bottom collision
            end else if (ball_dir_y == 1) begin
                ball_y <= ball_y - BALL_SPEED;

            end else begin
                ball_y <= ball_y + BALL_SPEED;
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
            end else if (l_paddle_hit)  begin
                    ball_dir_x <= 0;
                    ball_x <= L_PADDLE_X + X;

            // right paddle collision
            end else if (r_paddle_hit) begin
                ball_dir_x <= 1;
                ball_x <= R_PADDLE_X - X;

            // NO paddle collision
            end else if (ball_dir_x == 0) begin
                ball_x <= ball_x + BALL_SPEED;
            end else begin
                ball_x <= ball_x - BALL_SPEED;
            end


            // left paddle movement
            if (l_paddle_down && !l_paddle_up) begin
                if (l_paddle_y + PADDLE_HEIGHT + PADDLE_SPEED <= V_DISPLAY) begin
                    l_paddle_y <= l_paddle_y + PADDLE_SPEED;
                end else begin
                    l_paddle_y <= V_DISPLAY - PADDLE_HEIGHT; // paddle almost at bottom ==> set paddle at bottom
                end

            end else if (!l_paddle_down && l_paddle_up) begin
                if (l_paddle_y >= PADDLE_SPEED) begin
                    l_paddle_y <= l_paddle_y - PADDLE_SPEED;
                end else begin
                    l_paddle_y <= 0;
                end
            end

            // right paddle movement
            if (r_paddle_down && !r_paddle_up) begin
                if (r_paddle_y + PADDLE_HEIGHT + PADDLE_SPEED <= V_DISPLAY) begin // if not beyond the border
                    r_paddle_y <= r_paddle_y + PADDLE_SPEED;
                end else begin
                    r_paddle_y <= V_DISPLAY - PADDLE_HEIGHT; // set against bottom border
                end

            end else if (!r_paddle_down && r_paddle_up) begin
                if (r_paddle_y >= PADDLE_SPEED) begin
                    r_paddle_y <= r_paddle_y - PADDLE_SPEED;
                end else begin
                    r_paddle_y <= 0;
                end
            end



        end
    end
endmodule