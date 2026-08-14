module neural_net (clk, reset_n, ball_x, ball_y, ball_dir_x, ball_dir_y, paddle_y, paddle_up, paddle_down);

    // IO
    input wire clk;
    input wire reset_n;         // active low

    input wire [9:0] ball_x;
    input wire [9:0] ball_y;
    input wire       ball_dir_x; // 1 => to left, 0 => to right
    input wire       ball_dir_y; // 1 => to top, 0 => to bottom
    input wire [9:0] paddle_y;   // position of the paddle the net controls

    output reg paddle_up;
    output reg paddle_down;

    // Network shape. The weights/thresholds are placeholders here and get
    // frozen to their trained values at hardening.
    parameter N_IN  = 8;    // binary input features
    parameter N_HID = 8;    // hidden neurons
    parameter N_OUT = 2;    // outputs: {up, down}

    // Fixed weights, one bit per synapse ({0,1} represents {-1,+1})
    parameter [N_HID*N_IN-1:0]  W_HID = 64'hA5_3C_66_99_5A_C3_69_96;
    parameter [N_OUT*N_HID-1:0] W_OUT = 16'h6C_39;

    // Fixed neuron thresholds (4 bits each, compared against the XNOR popcount)
    parameter [N_HID*4-1:0] TH_HID = 32'h4444_4444;
    parameter [N_OUT*4-1:0] TH_OUT = 8'h44;

    // Binarize the game state into the input feature vector
    wire [N_IN-1:0] in_vec = {
        ball_y[9], ball_y[8], ball_y[7],  // coarse ball height
        paddle_y[9], paddle_y[8],         // coarse paddle height
        ball_x[9],                        // ball horizontal position (near/far)
        ball_dir_y,                       // ball vertical direction
        ball_dir_x                        // ball horizontal direction
    };

    // count the set bits of an 8-bit vector (a binary neuron's MAC)
    function [3:0] popcount8;
        input [7:0] v;
        integer k;
        begin
            popcount8 = 0;
            for (k = 0; k < 8; k = k + 1) begin
                popcount8 = popcount8 + v[k];
            end
        end
    endfunction

    // hidden layer: XNOR the inputs with each neuron's weights, popcount, threshold
    wire [N_HID-1:0] hid;
    genvar i;
    generate
        for (i = 0; i < N_HID; i = i + 1) begin : gen_hid
            assign hid[i] = (popcount8(~(in_vec ^ W_HID[i*N_IN +: N_IN])) >= TH_HID[i*4 +: 4]);
        end
    endgenerate

    // output layer: same operation on the hidden activations
    wire [N_OUT-1:0] out;
    generate
        for (i = 0; i < N_OUT; i = i + 1) begin : gen_out
            assign out[i] = (popcount8(~(hid ^ W_OUT[i*N_HID +: N_HID])) >= TH_OUT[i*4 +: 4]);
        end
    endgenerate

    // register the paddle decision
    always @(posedge clk) begin
        if (!reset_n) begin
            paddle_up   <= 1'b0;
            paddle_down <= 1'b0;
        end else begin
            paddle_up   <= out[0];
            paddle_down <= out[1];
        end
    end

endmodule
