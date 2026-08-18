`default_nettype none
`timescale 1ns / 1ps

/* This branch tests neural_net in isolation: neural_net is instantiated
   directly as the module under test (its own top-level ports only), so
   test_neural_net.py never has to reach into project.v's internal
   instances (dut.user_project.nn_inst, ...) to drive or observe it.
*/
module tb ();

  // Dump the signals to a FST file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg reset_n;
  reg frame_tick;
  reg [9:0] ball_y;
  reg ball_dir_x;
  reg ball_dir_y;
  reg [9:0] paddle_y;
  wire paddle_up;
  wire paddle_down;

  neural_net neural_net_inst (
      .clk        (clk),
      .reset_n    (reset_n),
      .frame_tick (frame_tick),
      .ball_y     (ball_y),
      .ball_dir_x (ball_dir_x),
      .ball_dir_y (ball_dir_y),
      .paddle_y   (paddle_y),
      .paddle_up  (paddle_up),
      .paddle_down(paddle_down)
  );

endmodule
