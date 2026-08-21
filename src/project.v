/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_neuropong (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  wire l_paddle_up = ui_in[0];
  wire l_paddle_down = ui_in[1];
  wire game_reset = ui_in[4];   // player button to restart the game

  // Unused inputs (the right paddle is driven by the neural net, ui_in[2:3] free)
  wire _unused = &{ena, ui_in[7:5], ui_in[3:2], uio_in, 1'b0};

  assign uio_out = 8'b0000_0000;
  assign uio_oe = 8'b0000_0000;

  
  // INTERNAL CONNECTIONS

  wire [9:0] h_count;
  wire [9:0] v_count;
  wire       hsync;
  wire       vsync;
  wire       draw_enable;
  wire       frame_tick;

  wire [9:0] l_paddle_y;
  wire [9:0] r_paddle_y;
  wire [9:0] ball_x;
  wire [9:0] ball_y;
  wire       ball_dir_x;
  wire       ball_dir_y;
  wire [3:0] l_score;
  wire [3:0] r_score;
  wire       winner;
  wire       game_over;    

  // neural net opponent drives the right paddle
  wire nn_paddle_up;
  wire nn_paddle_down;

  wire [1:0] red;
  wire [1:0] green;
  wire [1:0] blue;

  VGA_sync sync_inst (
      .clk        (clk),
      .reset_n    (rst_n),
      .h_count    (h_count),
      .v_count    (v_count),
      .hsync      (hsync),
      .vsync      (vsync),
      .draw_enable(draw_enable),
      .frame_tick  (frame_tick)
  );

  pong_logic pong_inst (
      .clk          (clk),
      .reset_n      (rst_n),
      .game_reset   (game_reset),
      .frame_tick   (frame_tick),
      .l_paddle_up  (l_paddle_up),
      .l_paddle_down(l_paddle_down),
      .r_paddle_up  (nn_paddle_up),
      .r_paddle_down(nn_paddle_down),
      .l_paddle_y   (l_paddle_y),
      .r_paddle_y   (r_paddle_y),
      .ball_x       (ball_x),
      .ball_y       (ball_y),
      .ball_dir_x   (ball_dir_x),
      .ball_dir_y   (ball_dir_y),
      .l_score      (l_score),
      .r_score      (r_score),
      .winner       (winner),
      .game_over    (game_over)
  );

  neural_net nn_inst (
      .clk        (clk),
      .reset_n    (rst_n),
      .frame_tick (frame_tick),
      .ball_y     (ball_y),
      .ball_dir_x (ball_dir_x),
      .ball_dir_y (ball_dir_y),
      .paddle_y   (r_paddle_y),
      .paddle_up  (nn_paddle_up),
      .paddle_down(nn_paddle_down)
  );

  render render_inst (
      .clk        (clk),
      .reset_n    (rst_n),
      .h_count    (h_count),
      .v_count    (v_count),
      .draw_enable(draw_enable),
      .l_paddle_y (l_paddle_y),
      .r_paddle_y (r_paddle_y),
      .ball_x     (ball_x),
      .ball_y     (ball_y),
      .l_score    (l_score),
      .r_score    (r_score),
      .winner     (winner),
      .game_over  (game_over),
      .red        (red),
      .green      (green),
      .blue       (blue)
  );



  // All output pins 
  assign uo_out[0] = red[1];
  assign uo_out[1] = green[1];
  assign uo_out[2] = blue[1];
  assign uo_out[3] = vsync;
  assign uo_out[4] = red[0];
  assign uo_out[5] = green[0];
  assign uo_out[6] = blue[0];
  assign uo_out[7] = hsync;
  


endmodule
