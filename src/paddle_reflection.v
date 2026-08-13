`ifndef REFLECTION
`define REFLECTION

module paddle_reflection(ball_y, paddle_y, l_paddle_collision, r_paddle_collision, reflection_vx, reflection_vy);
    
    input reg [9:0] ball_y;
    input reg [9:0] paddle_y;
    input wire l_paddle_collision;
    input wire r_paddle_collision;

    output reg signed [3:0] reflection_vx;
    output reg signed [3:0] reflection_vy;


    parameter [9:0] X = 15;

    reg [6:0] relative_position;
    reg [9:0] diff; // extra diff variable to avoid warning
    reg signed [3:0] vx_abs;

    always @(*) begin

    /*
    
     vx   vy   relative_position   width 
     ───────────────────────────────────
     +5   -5         1-12           12    
     +6   -4        13-25           13    
     +7   -2        26-38           13    
     +7    0        39-51           13    
     +7   +2        52-64           13    
     +6   +4        65-77           13    
     +5   +5        78-89           12    

    */

        reflection_vx = 0;
        reflection_vy = 0;
        vx_abs = 0;

        diff = ball_y - paddle_y + X;

        relative_position = diff [6:0];

        

        if (relative_position >= 1 && relative_position <= 12) begin
            vx_abs = 5;
            reflection_vy = -5;
        end
        else if (relative_position >= 13 && relative_position <= 25) begin
            vx_abs = 6;
            reflection_vy = -4;
        end
        else if (relative_position >= 26 && relative_position <= 38) begin
            vx_abs = 7;
            reflection_vy = -2;
        end
        else if (relative_position >= 39 && relative_position <= 51) begin
            vx_abs = 7;
            reflection_vy = 0;
        end
        else if (relative_position >= 52 && relative_position <= 64) begin
            vx_abs = 7;
            reflection_vy = +2;
        end
        else if (relative_position >= 65 && relative_position <= 77) begin
            vx_abs = 6;
            reflection_vy = +4;
        end
        else if (relative_position >= 78 && relative_position <= 89) begin
            vx_abs = 5;
            reflection_vy = +5;
        end




        if (l_paddle_collision) begin
            reflection_vx = vx_abs;
        end
        else if (r_paddle_collision) begin
            reflection_vx = -vx_abs;
        end
        

    end


endmodule

`endif