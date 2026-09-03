module neural_net (clk, reset_n, frame_tick, ball_y, ball_dir_x, ball_dir_y, paddle_y, weight_load, weight_in, paddle_up, paddle_down);

    // IO
    input wire clk;
    input wire reset_n;         // active low
    input wire frame_tick;

    input wire [9:0] ball_y;
    input wire ball_dir_x; // 1 => to left, 0 => to right
    input wire ball_dir_y; // 1 => to top, 0 => to bottom
    input wire [9:0] paddle_y;   // (neural net paddle)

    input wire weight_load; // shift weight_in into the weight chain on every clk while high
    input wire weight_in;   // serial weight bit, MSB first

    output reg paddle_up;
    output reg paddle_down;

    // Ternary neural network
    // Weights are reprogrammable post-hardening via weight_load/weight_in; thresholds stay fixed.
    parameter N_IN  = 3;    // ternary input features
    parameter N_HID = 8;    // hidden neurons
    parameter N_OUT = 2;    // outputs: {up, down}

    // How far the ball may drift from the paddle before it counts as aligned / above or below
    parameter DEAD_ZONE = 30;

    // Ternary weight encoding
    localparam [1:0] WP = 2'b01; // +1
    localparam [1:0] WZ = 2'b00; //  0
    localparam [1:0] WN = 2'b10; // -1

    localparam W_HID_BITS = N_HID*N_IN*2;   // 48
    localparam W_OUT_BITS = N_OUT*N_HID*2;  // 32
    localparam W_BITS     = W_HID_BITS + W_OUT_BITS;

    // Trained ternary weights, held in a shift register so they can be
    // reloaded after hardening. Holding weight_load high for W_BITS clocks
    // while feeding weight_in shifts a new W_HID ++ W_OUT vector in, MSB first.
    reg [W_BITS-1:0] weight_shift;
    always @(posedge clk) begin
        if (!reset_n) begin
            weight_shift <= {
                // Hidden layer, 3 weights (dir_x, dir_y, diff) per neuron
                WZ, WN, WP,
                WZ, WN, WP,
                WZ, WZ, WP,
                WZ, WZ, WP,
                WZ, WZ, WP,
                WZ, WZ, WP,
                WZ, WZ, WP,
                WZ, WZ, WP,
                // Output layer, 8 weights (one per hidden neuron) per output
                WP, WP, WP, WP, WP, WP, WP, WP,
                WN, WN, WN, WN, WN, WN, WN, WN
            };
        end else if (weight_load) begin
            weight_shift <= {weight_shift[W_BITS-2:0], weight_in};
        end
    end

    wire [W_HID_BITS-1:0] W_HID = weight_shift[W_BITS-1 -: W_HID_BITS];
    wire [W_OUT_BITS-1:0] W_OUT = weight_shift[W_OUT_BITS-1:0];

    // Fixed neuron thresholds (signed)
    parameter signed [N_HID*3-1:0] TH_HID_POS = {8{3'sd1}};
    parameter signed [N_HID*3-1:0] TH_HID_NEG = {8{-3'sd1}};
    parameter signed [N_OUT*4-1:0] TH_OUT = {4'sd4, 4'sd4};

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

    // Pipeline: frame_tick only pulses once per video frame, so the net is
    // split into three clock-registered stages instead of one combinatoric
    // block.
    reg valid_hid, valid_out;
    always @(posedge clk) begin
        if (!reset_n) begin
            valid_hid <= 1'b0;
            valid_out <= 1'b0;
        end else begin
            valid_hid <= frame_tick;
            valid_out <= valid_hid;
        end
    end

    // Binarize/ternarize the game state into the input feature vector
    wire signed [10:0] diff = $signed({1'b0, ball_y}) - $signed({1'b0, paddle_y});

    wire signed [1:0] t_diff = (diff >  DEAD_ZONE) ?  2'sd1 :
                                 (diff < -DEAD_ZONE) ? -2'sd1 : 2'sd0; // To prevent 'tremors' in paddle control
    wire signed [1:0] t_dir_y = ball_dir_y ? 2'sd1 : -2'sd1;
    wire signed [1:0] t_dir_x = ball_dir_x ? 2'sd1 : -2'sd1;

    // Stage 1: latch the input feature vector on frame_tick
    reg signed [1:0] in_vec [0:N_IN-1];
    always @(posedge clk) begin
        if (!reset_n) begin
            in_vec[0] <= 2'sd0;
            in_vec[1] <= 2'sd0;
            in_vec[2] <= 2'sd0;
        end else if (frame_tick) begin
            in_vec[0] <= t_diff;
            in_vec[1] <= t_dir_y;
            in_vec[2] <= t_dir_x;
        end
    end

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

    // Stage 2: latch the hidden layer outputs
    reg signed [1:0] hid_r [0:N_HID-1];
    generate
        for (i = 0; i < N_HID; i = i + 1) begin : gen_hid_reg
            always @(posedge clk) begin
                if (!reset_n) hid_r[i] <= 2'sd0;
                else if (valid_hid) hid_r[i] <= hid[i];
            end
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
            wire signed [3:0] w4 = trit(W_OUT[(i*N_HID+4)*2 +: 2]);
            wire signed [3:0] w5 = trit(W_OUT[(i*N_HID+5)*2 +: 2]);
            wire signed [3:0] w6 = trit(W_OUT[(i*N_HID+6)*2 +: 2]);
            wire signed [3:0] w7 = trit(W_OUT[(i*N_HID+7)*2 +: 2]);
            wire signed [4:0] mac = hid_r[0]*w0 + hid_r[1]*w1 + hid_r[2]*w2 + hid_r[3]*w3 +
                                    hid_r[4]*w4 + hid_r[5]*w5 + hid_r[6]*w6 + hid_r[7]*w7;
            assign out[i] = (mac >= $signed(TH_OUT[i*4 +: 4]));
        end
    endgenerate

    // Stage 3: register the paddle decision
    always @(posedge clk) begin
        if (!reset_n) begin
            paddle_up <= 1'b0;
            paddle_down <= 1'b0;
        end else if (valid_out) begin
            if (out[0]) begin
                paddle_up <= out[0];
                paddle_down <= 0;
            end else if (out[1]) begin
                paddle_up <= 0;
                paddle_down <= out[1];
            end else begin
                paddle_up <= 0;
                paddle_down <= 0;
            end
        end
    end

endmodule
