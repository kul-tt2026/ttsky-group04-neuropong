module neural_net (clk, reset_n, frame_tick, ball_y, ball_dir_x, ball_dir_y, paddle_y, paddle_up, paddle_down);

    // IO
    input wire clk;
    input wire reset_n;         // active low
    input wire frame_tick;

    input wire [9:0] ball_y;
    input wire ball_dir_x; // 1 => to left, 0 => to right
    input wire ball_dir_y; // 1 => to top, 0 => to bottom
    input wire [9:0] paddle_y;   // (neural net paddle)

    output reg paddle_up;
    output reg paddle_down;

    // Ternary neural network
    // Weights & thresholds are currently frozen at hardening.
    parameter N_IN  = 3;    // ternary input features
    parameter N_HID = 4;    // hidden neurons
    parameter N_OUT = 2;    // outputs: {up, down}

    // How far the ball may drift from the paddle before it counts as
    // "aligned" (trit 0) rather than above/below (trit -1/+1).
    parameter DEAD_ZONE = 30;

    // Fixed ternary weights
    parameter [N_HID*N_IN*2-1:0] W_HID = 24'h251141; // PLACEHOLDER!! 
    parameter [N_OUT*N_HID*2-1:0] W_OUT = 16'h55AA;  // PLACEHOLDER!! 

    // Fixed neuron thresholds (signed)
    parameter signed [N_HID*3-1:0] TH_HID_POS = 12'h491;
    parameter signed [N_HID*3-1:0] TH_HID_NEG = 12'hDB7; 
    parameter signed [N_OUT*4-1:0] TH_OUT = 8'h11;  

    // decode a 2-bit ternary code into a signed trit value
    function signed [1:0] trit;
        input [1:0] code;
        begin
            case (code)
                2'b01: trit =  2'sd1;
                2'b10: trit = -2'sd1;
                default: trit =  2'sd0;
            endcase
        end
    endfunction

    // Binarize/ternarize the game state into the input feature vector
    wire signed [10:0] diff = $signed({1'b0, ball_y}) - $signed({1'b0, paddle_y});

    wire signed [1:0] t_diff = (diff >  DEAD_ZONE) ?  2'sd1 :
                                 (diff < -DEAD_ZONE) ? -2'sd1 : 2'sd0; // To prevent 'tremors' in paddle control
    wire signed [1:0] t_dir_y = ball_dir_y ? 2'sd1 : -2'sd1;
    wire signed [1:0] t_dir_x = ball_dir_x ? 2'sd1 : -2'sd1;

    wire signed [1:0] in_vec [0:N_IN-1];
    assign in_vec[0] = t_diff;
    assign in_vec[1] = t_dir_y;
    assign in_vec[2] = t_dir_x;

    // Hidden layer logic
    wire signed [1:0] hid [0:N_HID-1];
    genvar i;
    generate
        for (i = 0; i < N_HID; i = i + 1) begin : gen_hid
            wire signed [3:0] w0 = trit(W_HID[(i*N_IN+0)*2 +: 2]);
            wire signed [3:0] w1 = trit(W_HID[(i*N_IN+1)*2 +: 2]);
            wire signed [3:0] w2 = trit(W_HID[(i*N_IN+2)*2 +: 2]);
            wire signed [3:0] mac = in_vec[0]*w0 + in_vec[1]*w1 + in_vec[2]*w2;
            assign hid[i] = (mac >= $signed(TH_HID_POS[i*3 +: 3])) ?  2'sd1 :
                             (mac <= $signed(TH_HID_NEG[i*3 +: 3])) ? -2'sd1 : 2'sd0;
        end
    endgenerate

    // Output layer logic
    wire [N_OUT-1:0] out;
    generate
        for (i = 0; i < N_OUT; i = i + 1) begin : gen_out
            wire signed [3:0] w0 = trit(W_OUT[(i*N_HID+0)*2 +: 2]);
            wire signed [3:0] w1 = trit(W_OUT[(i*N_HID+1)*2 +: 2]);
            wire signed [3:0] w2 = trit(W_OUT[(i*N_HID+2)*2 +: 2]);
            wire signed [3:0] w3 = trit(W_OUT[(i*N_HID+3)*2 +: 2]);
            wire signed [4:0] mac = hid[0]*w0 + hid[1]*w1 + hid[2]*w2 + hid[3]*w3;
            assign out[i] = (mac >= $signed(TH_OUT[i*4 +: 4])); // 2 bit output
        end
    endgenerate

    // register the paddle decision
    always @(posedge clk) begin
        if (!reset_n) begin
            paddle_up <= 1'b0;
            paddle_down <= 1'b0;
        end else if (frame_tick) begin
            if (out[0]) begin
                paddle_up <= out[0];
                paddle_down <= 0;
            end else if (output[1]) begin
                paddle_up <= 0; 
                paddle_down <= out[1];
            end else begin 
                paddle_up <= 0;
                paddle_down <= 0;
            end
        end
    end

endmodule
