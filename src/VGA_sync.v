`ifndef HVSYNC
`define HVSYNC

module sync(clk, reset, h_count, v_count , hsync, vsync, draw_enable);

    // IO
    input wire clk;
    input wire reset;
    output reg[9:0] h_count; // 0-799
    output reg[9:0] v_count; // 0-524
    output reg hsync;
    output reg vsync;
    output wire draw_enable;


    // front, back porch and sync lengths
    parameter V_DISPLAY = 480;
    parameter V_FRONT_PORCH = 10;
    parameter V_SYNC = 2;
    parameter V_BACK_PORCH = 33;

    parameter H_DISPLAY = 640;
    parameter H_FRONT_PORCH = 16;
    parameter H_SYNC = 96;
    parameter H_BACK_PORCH = 48;

    // front, back porch and sync lengths pos
    parameter V_SYNC_BEGIN = V_DISPLAY + V_FRONT_PORCH;
    parameter V_SYNC_END = V_DISPLAY + V_FRONT_PORCH + V_SYNC - 1; // include -1 because started from 0

    parameter H_SYNC_BEGIN = H_DISPLAY + H_FRONT_PORCH;
    parameter H_SYNC_END = H_DISPLAY + H_FRONT_PORCH + H_SYNC - 1;

    wire h_max = (h_count == H_SYNC_END + H_BACK_PORCH);
    wire v_max = (v_count == V_SYNC_END + V_BACK_PORCH);


    assign draw_enable = (h_count < H_DISPLAY) && (v_count < V_DISPLAY);

    always @(posedge clk) begin

        if (reset)begin
            h_count <= 0;
            v_count <= 0;
            hsync <= 1'b1;
            vsync <= 1'b1;

        end else begin

            hsync <= ~(H_SYNC_BEGIN <= h_count && H_SYNC_END >= h_count);
            vsync <= ~(V_SYNC_BEGIN <= v_count && V_SYNC_END >= v_count);

            

            if (h_max) begin
                h_count <= 0;

                if (v_max) begin
                    v_count <= 0;

                end else begin
                    v_count <= 1 + v_count;
                end

            end else begin
                h_count <= 1 + h_count;

            end
        end
    end



endmodule

`endif