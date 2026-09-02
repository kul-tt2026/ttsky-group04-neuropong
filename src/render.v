module render(clk, reset_n, h_count, v_count, draw_enable, l_paddle_y, r_paddle_y, ball_x, ball_y, l_score, r_score, winner, game_over, red, green, blue);

    // IO
    input wire clk;
    input wire reset_n; // active low

    input wire [9:0] h_count;
    input wire [9:0] v_count;
    input wire draw_enable;

    input wire [9:0] l_paddle_y;
    input wire [9:0] r_paddle_y;
    input wire [9:0] ball_x;        //position of top left corner
    input wire [9:0] ball_y;
    input wire [3:0] l_score;
    input wire [3:0] r_score;
    input wire winner;
    input wire game_over;

    output reg [1:0] red;
    output reg [1:0] green;
    output reg [1:0] blue;

    parameter H_DISPLAY = 640;
    parameter V_DISPLAY = 480;
    parameter H_CENTER = H_DISPLAY / 2;

    parameter X = 15;
    parameter DASH_SIZE = 20;
    parameter L_PADDLE_X = 2*X;
    parameter R_PADDLE_X = H_DISPLAY - 3*X;

    wire ball_in = (h_count >= ball_x && h_count < ball_x + X) && (v_count >= ball_y && v_count < ball_y + X);
    wire l_paddle_in = (h_count >= L_PADDLE_X && h_count < L_PADDLE_X + X) && (v_count >= l_paddle_y && v_count < l_paddle_y + 5*X);
    wire r_paddle_in = (h_count >= R_PADDLE_X && h_count < R_PADDLE_X + X) && (v_count >= r_paddle_y && v_count < r_paddle_y + 5*X);

    wire border_line = (h_count < 2)|| (h_count >= H_DISPLAY - 2) || (v_count < 2) || (v_count >= V_DISPLAY - 2);
    wire center_line = (h_count >= H_CENTER - 1 && h_count <= H_CENTER + 1) && ((v_count / DASH_SIZE) % 2 == 0) && (v_count < V_DISPLAY);

    wire draw_score;
    score_render score_inst (
        .h_count(h_count),
        .v_count(v_count),
        .l_score(l_score),
        .r_score(r_score),
        .draw_score(draw_score)
    );

    wire draw_wins;
    wins_render wins_inst (
        .h_count(h_count),
        .v_count(v_count),
        .draw_wins(draw_wins)
    );

    wire draw_blue;
    blue_render blue_inst (
        .h_count(h_count),
        .v_count(v_count),
        .draw_blue(draw_blue)
    );

    wire draw_red;
    red_render red_inst (
        .h_count(h_count),
        .v_count(v_count),
        .draw_red(draw_red)
    );
    
    always @(posedge clk) begin
        if (!reset_n) begin
            red <= 2'b00;
            green <= 2'b00;
            blue <= 2'b00;

        end else begin
            if (draw_enable) begin
                if (game_over) begin
                    if (draw_wins) begin
                        red <= 2'b11;
                        green <= 2'b11;
                        blue <= 2'b11;
                    end else if (winner) begin
                        // right player won
                        if (draw_blue) begin
                            red <= 2'b11;
                            green <= 2'b11;
                            blue <= 2'b11;
                        end else begin
                            red <= 2'b00;
                            green <= 2'b00;
                            blue <= 2'b11;
                        end
                    end else begin
                        // left player won
                        if (draw_red) begin
                            red <= 2'b11;
                            green <= 2'b11;
                            blue <= 2'b11;
                        end else begin
                            red <= 2'b11;
                            green <= 2'b00;
                            blue <= 2'b00;
                        end
                    end
                end else begin
                    // ball
                    if (ball_in) begin
                        red <= 2'b11;
                        green <= 2'b11;
                        blue <= 2'b11;
                    // border line
                    end else if (border_line) begin
                        red <= 2'b10;
                        green <= 2'b10;
                        blue <= 2'b10;
                    // center line
                    end else if (center_line) begin
                        red <= 2'b10;
                        green <= 2'b10;
                        blue <= 2'b10;
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
                    // scores
                    end else if (draw_score) begin
                        red <= 2'b10;
                        green <= 2'b10;
                        blue <= 2'b10;
                    // background
                    end else begin
                        red <= 2'b00;
                        green <= 2'b00;
                        blue <= 2'b00;
                    end
                end
                end else begin
                    red <= 2'b00;
                    green <= 2'b00;
                    blue <= 2'b00;
                end
            end
        end


endmodule