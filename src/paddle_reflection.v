`ifndef REFLECTION
`define REFLECTION

module paddle_reflection(ball_y, paddle_y, l_paddle_collision, r_paddle_collision, reflection_vx, reflection_vy);
    
    input wire [9:0] ball_y;
    input wire [9:0] paddle_y;
    input wire l_paddle_collision;
    input wire r_paddle_collision;

    output reg signed [9:0] reflection_vx;
    output reg signed [9:0] reflection_vy;


    parameter [9:0] X = 15;

    reg [6:0] relative_position;
    reg [9:0] diff; // extra diff variable to avoid warning
    reg signed [9:0] vx_abs;

    always @(*) begin

    /*

    Absolute Speed is 7 px/frame
    
     vx   vy   relative_position   width 
     ───────────────────────────────────
     +5   -5        1-8            8    
     +6   -4        9-19           11    
     +6   -3        20-31          12 
     +7   -2        32-42          11   
     +7    0        43-47          5    
     +7   +2        48-58          11
     +6   +3        59-70          12    
     +6   +4        71-81          11    
     +5   +5        82-89          8    

    */

        reflection_vx = 0;
        reflection_vy = 0;
        vx_abs = 0;

        diff = ball_y - paddle_y + X;

        relative_position = diff [6:0];

        

        if (relative_position <= 8) begin
            vx_abs = 5;
            reflection_vy = -5;
        end
        else if (relative_position >= 9 && relative_position <= 19) begin
            vx_abs = 6;
            reflection_vy = -4;
        end
        else if (relative_position >= 20 && relative_position <= 31) begin
            vx_abs = 6;
            reflection_vy = -3;
        end
        else if (relative_position >= 32 && relative_position <= 42) begin
            vx_abs = 7;
            reflection_vy = -2;
        end
        else if (relative_position >= 43 && relative_position <= 47) begin
            vx_abs = 7;
            reflection_vy = 0;
        end
        else if (relative_position >= 48 && relative_position <= 58) begin
            vx_abs = 7;
            reflection_vy = +2;
        end
        else if (relative_position >= 59 && relative_position <= 70) begin
            vx_abs = 6;
            reflection_vy = +3;
        end
        else if (relative_position >= 71 && relative_position <= 81) begin
            vx_abs = 6;
            reflection_vy = +4;
        end
        else if (relative_position >= 82) begin
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