module score_render (h_count, v_count, l_score, r_score, draw_score);
    input wire [9:0] h_count;
    input wire [9:0] v_count;
    input wire [3:0] l_score;
    input wire [3:0] r_score;

    output wire draw_score;

    reg [6:0] l_seg;
    reg [6:0] r_seg;


    // to 7-segment display
    // left score
    always @(*) begin
        case (l_score)
            4'd0: l_seg = 7'b1111110; 4'd1: l_seg = 7'b0110000; 4'd2: l_seg = 7'b1101101;
            4'd3: l_seg = 7'b1111001; 4'd4: l_seg = 7'b0110011; 4'd5: l_seg = 7'b1011011;
            4'd6: l_seg = 7'b1011111; 4'd7: l_seg = 7'b1110000; 4'd8: l_seg = 7'b1111111;
            4'd9: l_seg = 7'b1111011; default: l_seg = 7'b0000000;
        endcase
    end

    // right score
    always @(*) begin
        case (r_score)
            4'd0: r_seg = 7'b1111110; 4'd1: r_seg = 7'b0110000; 4'd2: r_seg = 7'b1101101;
            4'd3: r_seg = 7'b1111001; 4'd4: r_seg = 7'b0110011; 4'd5: r_seg = 7'b1011011;
            4'd6: r_seg = 7'b1011111; 4'd7: r_seg = 7'b1110000; 4'd8: r_seg = 7'b1111111;
            4'd9: r_seg = 7'b1111011; default: r_seg = 7'b0000000;
        endcase
    end

    // each segment left
    wire l_seg_A = (h_count >= 254 && h_count < 276 && v_count >= 30  && v_count < 34);
    wire l_seg_B = (h_count >= 276 && h_count < 280 && v_count >= 34  && v_count < 53);
    wire l_seg_C = (h_count >= 276 && h_count < 280 && v_count >= 57  && v_count < 76);
    wire l_seg_D = (h_count >= 254 && h_count < 276 && v_count >= 76  && v_count < 80);
    wire l_seg_E = (h_count >= 250 && h_count < 254 && v_count >= 57  && v_count < 76);
    wire l_seg_F = (h_count >= 250 && h_count < 254 && v_count >= 34  && v_count < 53);
    wire l_seg_G = (h_count >= 254 && h_count < 276 && v_count >= 53  && v_count < 57);

    wire draw_l_score = (l_seg[6] && l_seg_A) || (l_seg[5] && l_seg_B) || (l_seg[4] && l_seg_C) ||
                        (l_seg[3] && l_seg_D) || (l_seg[2] && l_seg_E) || (l_seg[1] && l_seg_F) || (l_seg[0] && l_seg_G);

    // each segment right
    wire r_seg_A = (h_count >= 364 && h_count < 386 && v_count >= 30  && v_count < 34);
    wire r_seg_B = (h_count >= 386 && h_count < 390 && v_count >= 34  && v_count < 53);
    wire r_seg_C = (h_count >= 386 && h_count < 390 && v_count >= 57  && v_count < 76);
    wire r_seg_D = (h_count >= 364 && h_count < 386 && v_count >= 76  && v_count < 80);
    wire r_seg_E = (h_count >= 360 && h_count < 364 && v_count >= 57  && v_count < 76);
    wire r_seg_F = (h_count >= 360 && h_count < 364 && v_count >= 34  && v_count < 53);
    wire r_seg_G = (h_count >= 364 && h_count < 386 && v_count >= 53  && v_count < 57);

    wire draw_r_score = (r_seg[6] && r_seg_A) || (r_seg[5] && r_seg_B) || (r_seg[4] && r_seg_C) ||
                        (r_seg[3] && r_seg_D) || (r_seg[2] && r_seg_E) || (r_seg[1] && r_seg_F) || (r_seg[0] && r_seg_G);

    // if (h_count, v_count) is the pixel of one of the scores
    assign draw_score = draw_l_score || draw_r_score;
    
endmodule