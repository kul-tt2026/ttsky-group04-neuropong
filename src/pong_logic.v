module pong_logic (clk, reset_n, game_reset, frame_tick, l_paddle_up, l_paddle_down, r_paddle_up, r_paddle_down, l_paddle_y, r_paddle_y, ball_x, ball_y, ball_dir_x, ball_dir_y, l_score, r_score, winner, game_over);
    input wire clk;
    input wire reset_n;     // active low, resets the whole chip
    input wire game_reset;  // active high, restarts the game (scores + positions)
    input wire frame_tick;

    input wire l_paddle_up;
    input wire l_paddle_down;

    input wire r_paddle_up;
    input wire r_paddle_down;

    output reg [9:0] l_paddle_y;
    output reg [9:0] r_paddle_y;

    output reg [9:0] ball_x;
    output reg [9:0] ball_y;

    output wire ball_dir_x; // 1 => to left, 0 => to right
    output wire ball_dir_y; // 1 => to top, 0 => to bottom

    output reg [3:0] l_score;
    output reg [3:0] r_score;

    output reg winner; // 0 => left player won, 1 => right player won
    output reg game_over;

    parameter V_DISPLAY = 480;
    parameter H_DISPLAY = 640;

    parameter X = 15;
    parameter L_PADDLE_X = 2*X;
    parameter R_PADDLE_X = H_DISPLAY - 3*X;
    parameter PADDLE_HEIGHT = 5*X;

    parameter PADDLE_SPEED = 5;

    parameter GAME_OVER_FRAMES = 180; // 3 seconds

    reg [7:0] pause_counter;

    reg frame_phase;

    reg l_paddle_hit, r_paddle_hit;
    reg l_front_hit,  r_front_hit;

    reg signed [9:0] ball_vx;
    reg signed [9:0] ball_vy;

    wire signed [9:0] reflection_vx;
    wire signed [9:0] reflection_vy;

    wire top_hit = (ball_y <= abs_ball_vy && ball_vy < 0);
    wire bottom_hit = (ball_y + X + abs_ball_vy >= V_DISPLAY && ball_vy > 0);

    wire [9:0] pred_x = ball_x + ball_vx;
    wire [9:0] pred_y = ball_y + ball_vy;

    wire [9:0] l_x_overlap = (pred_x + X < L_PADDLE_X + X ? pred_x + X : L_PADDLE_X + X) - (pred_x > L_PADDLE_X ? pred_x : L_PADDLE_X);
    wire [9:0] l_y_overlap = (pred_y + X < l_paddle_y + PADDLE_HEIGHT ? pred_y + X : l_paddle_y + PADDLE_HEIGHT) - (pred_y > l_paddle_y ? pred_y : l_paddle_y);
 
    wire [9:0] r_x_overlap = (pred_x + X < R_PADDLE_X + X ? pred_x + X : R_PADDLE_X + X) - (pred_x > R_PADDLE_X ? pred_x : R_PADDLE_X);
    wire [9:0] r_y_overlap = (pred_y + X < r_paddle_y + PADDLE_HEIGHT ? pred_y + X : r_paddle_y + PADDLE_HEIGHT) - (pred_y > r_paddle_y ? pred_y : r_paddle_y);

    assign ball_dir_x = ball_vx[9]; // msb decides the sign
    assign ball_dir_y = ball_vy[9]; 

    wire [9:0] abs_ball_vx = ball_vx[9] ? -ball_vx : ball_vx;
    wire [9:0] abs_ball_vy = ball_vy[9] ? -ball_vy : ball_vy;

    // Paddle reflection
    wire [9:0] selected_paddle_y = l_paddle_hit ? l_paddle_y : r_paddle_y;

    paddle_reflection refl_inst (
        .ball_y(ball_y),
        .paddle_y(selected_paddle_y),
        .l_paddle_collision(l_paddle_hit),
        .r_paddle_collision(r_paddle_hit),
        .reflection_vx(reflection_vx),
        .reflection_vy(reflection_vy)
    );


    // Pipeline: check for collisions (sequential)
    always @(posedge clk) begin
        if (!reset_n || game_reset) begin
            l_paddle_hit <= 1'b0;
            r_paddle_hit <= 1'b0;
            l_front_hit  <= 1'b0;
            r_front_hit  <= 1'b0;
        end else begin
            l_paddle_hit <= (ball_vx < 0) && 
                            (ball_x <= L_PADDLE_X + X + abs_ball_vx && ball_x + X >= L_PADDLE_X) && 
                            (ball_y + X >= l_paddle_y && ball_y < l_paddle_y + PADDLE_HEIGHT);

            r_paddle_hit <= (ball_vx > 0) && 
                            (ball_x <= R_PADDLE_X + X && ball_x + X + abs_ball_vx >= R_PADDLE_X) && 
                            (ball_y + X >= r_paddle_y && ball_y < r_paddle_y + PADDLE_HEIGHT);

            l_front_hit  <= (l_x_overlap <= l_y_overlap);
            r_front_hit  <= (r_x_overlap <= r_y_overlap);
        end
    end


    always @(posedge clk) begin

        // full chip reset or a player-triggered game restart
        if (!reset_n || game_reset) begin
            l_paddle_y <= V_DISPLAY/2 - 3*X/2;
            r_paddle_y <= V_DISPLAY/2 - 3*X/2;

            ball_x <= H_DISPLAY/2 - X/2;
            ball_y <= V_DISPLAY/2 - X/2;

            ball_vx <= -10'sd3;
            ball_vy <= 10'sd2;
            pause_counter <= 8'b0;
            game_over <= 1'b0;
            winner <= 1'b0;

            frame_phase <= 1'b0;

            l_score <= 4'd0;
            r_score <= 4'd0;

        end else if (frame_tick) begin

            if (game_over) begin
                if (pause_counter == GAME_OVER_FRAMES) begin
                    l_paddle_y <= V_DISPLAY/2 - 3*X/2;
                    r_paddle_y <= V_DISPLAY/2 - 3*X/2;

                    ball_x <= H_DISPLAY/2 - X/2;
                    ball_y <= V_DISPLAY/2 - X/2;

                    if (frame_phase) begin
                        ball_vx <= 10'sd3;
                    end else begin
                        ball_vx <= -10'sd3;
                    end
                    ball_vy <= 10'sd2;

                    l_score <= 4'd0;
                    r_score <= 4'd0;
                    game_over <= 1'b0;
                    pause_counter <= 8'b0;
                    winner <= 1'b0;

                end else begin
                    pause_counter <= pause_counter + 1;
                end
            end else begin

                frame_phase <= ~frame_phase; // used for randomizing

            // Y-axis LOGIC
                // top border collision
                if (top_hit) begin
                    ball_vy <= -ball_vy;
                    ball_y <= abs_ball_vy - ball_y;      // rebounce of border

                // bottom border collision
                end else if (bottom_hit) begin
                    ball_vy <= -ball_vy;
                    ball_y <= (V_DISPLAY - X) - ((ball_y + X + abs_ball_vy) - V_DISPLAY); // rebounce of border
                
                // NO top/bottom collision
                end else begin
                    ball_y <= ball_y + ball_vy;
                end

            // X-axis LOGIC
                // left border collision
                if (ball_x <= abs_ball_vx) begin        
                    ball_vx <= 10'sd3;               // give ball to the one who scored
                    if (frame_phase) begin
                        ball_vy <= 10'sd1;
                    end else begin
                        ball_vy <= -10'sd1;
                    end

                    ball_x <= H_DISPLAY/2 - X/2;
                    ball_y <= V_DISPLAY/2 - X/2;

                    if (r_score == 4'd9) begin
                        winner <= 1'b1; // right player won
                        game_over <= 1'b1;
                    end else begin
                        r_score <= r_score + 1;
                    end

                // right border collision
                end else if (ball_x + X + abs_ball_vx >= H_DISPLAY) begin
                    ball_vx <= -10'sd3;              // give ball to the one who scored
                    if (frame_phase) begin
                        ball_vy <= 10'sd1;
                    end else begin
                        ball_vy <= -10'sd1;
                    end

                    ball_x <= H_DISPLAY/2 - X/2;
                    ball_y <= V_DISPLAY/2 - X/2;

                    if (l_score == 4'd9) begin
                        winner <= 1'b0; // left player won
                        game_over <= 1'b1;
                    end else begin
                        l_score <= l_score + 1;
                    end

                // left paddle collision
                end else if (l_paddle_hit)  begin
                        ball_vx <= reflection_vx;
                        ball_vy <= reflection_vy;

                        if (l_front_hit) begin
                            ball_x <= L_PADDLE_X + X;
                        end else if (pred_y < l_paddle_y) begin
                            ball_y <= l_paddle_y - X;
                        end else begin
                            ball_y <= l_paddle_y + PADDLE_HEIGHT;
                        end
                    
                // right paddle collision
                end else if (r_paddle_hit) begin
                    ball_vx <= reflection_vx;
                    ball_vy <= reflection_vy;

                    if (r_front_hit) begin
                            ball_x <= R_PADDLE_X - X;
                    end else if (pred_y < r_paddle_y) begin
                        ball_y <= r_paddle_y - X;
                    end else begin
                        ball_y <= r_paddle_y + PADDLE_HEIGHT;
                    end
                    

                // NO paddle collision
                end else if (ball_dir_x == 0) begin
                    ball_x <= ball_x + abs_ball_vx;
                end else begin
                    ball_x <= ball_x - abs_ball_vx;
                end

            // Paddle movement LOGIC

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
    end
endmodule
