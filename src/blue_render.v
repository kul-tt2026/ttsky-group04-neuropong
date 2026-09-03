module blue_render (h_count, v_count, draw_blue);

 input wire [9:0] h_count;
 input wire [9:0] v_count;
 output wire draw_blue;

 parameter START_X = 32;
 parameter START_Y = 208;
 parameter FONT_SCALE = 8;

 /*
    Each letter is a 8x8 bitmap.
    There are 4 letters "blue" ==> 32x8
    Each letter is scaled by the factor FONT_SCALE
 */

 wire [9:0] rel_x = (h_count - START_X) / FONT_SCALE;
 wire [9:0] rel_y = (v_count - START_Y) / FONT_SCALE;

 wire in_bounds = (h_count >= START_X) && (h_count < START_X + (32 * FONT_SCALE)) && (v_count >= START_Y) && (v_count < START_Y + (8 * FONT_SCALE));

 wire [1:0] char_index = rel_x[4:3]; // 0=B, 1=L, 2=U, 3=E
 wire [2:0] char_x = rel_x[2:0]; // X-position in a letter
 wire [2:0] char_y = rel_y[2:0]; // Y-position in a letter

 reg [7:0] row_bits;

 always @(*) begin
    row_bits = 8'b00000000;
    case (char_index)
        2'b00: begin // 'B'
            case (char_y)
                3'd0: row_bits = 8'b00000000;
                3'd1: row_bits = 8'b11111100;
                3'd2: row_bits = 8'b10000010;
                3'd3: row_bits = 8'b10000010;
                3'd4: row_bits = 8'b11111100;
                3'd5: row_bits = 8'b10000010;
                3'd6: row_bits = 8'b10000010;
                3'd7: row_bits = 8'b11111100;
            endcase
        end
        2'b01: begin // 'L'
            case (char_y)
                3'd0: row_bits = 8'b00000000;
                3'd1: row_bits = 8'b01000000;
                3'd2: row_bits = 8'b01000000;
                3'd3: row_bits = 8'b01000000;
                3'd4: row_bits = 8'b01000000;
                3'd5: row_bits = 8'b01000000;
                3'd6: row_bits = 8'b01000000;
                3'd7: row_bits = 8'b01111110;
            endcase
        end
        2'b10: begin // 'U'
            case (char_y)
                3'd0: row_bits = 8'b00000000;
                3'd1: row_bits = 8'b10000010;
                3'd2: row_bits = 8'b10000010;
                3'd3: row_bits = 8'b10000010;
                3'd4: row_bits = 8'b10000010;
                3'd5: row_bits = 8'b10000010;
                3'd6: row_bits = 8'b10000010;
                3'd7: row_bits = 8'b00111100;
            endcase
        end
        2'b11: begin // 'E'
            case (char_y)
                3'd0: row_bits = 8'b00000000;
                3'd1: row_bits = 8'b01111110;
                3'd2: row_bits = 8'b01000000;
                3'd3: row_bits = 8'b01000000;
                3'd4: row_bits = 8'b01111100;
                3'd5: row_bits = 8'b01000000;
                3'd6: row_bits = 8'b01000000;
                3'd7: row_bits = 8'b01111110;
            endcase
        end
    endcase
end
    assign draw_blue = in_bounds && row_bits[7 - char_x];
endmodule

