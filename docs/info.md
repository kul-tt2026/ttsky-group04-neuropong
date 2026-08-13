<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

The chip implements a Pong game where you can play against an AI opponent. This chip requires a VGA screen and Tiny VGA Pmod for displaying the content.

As a player you control the left paddle and have two inputs, either you move your paddle up or move it down. If no input is given the paddle stays still. You stay in the game 
by reflecting the ball with your paddle back to the opponent. The further the ball hits a paddle from its center the sharper the angle of reflection of the ball wil be.
Use this to your advantage to win against your opponent. On the opposite side of the display an AI (ternary network) controls the right paddle. If you score 10 points 
by bouncing the ball such that the opponent can't intercept it, you win the game.

The different modules/functions used are:
    - pong_logic: defining the rules that make up the game Pong
    - paddle_reflection: giving the ball a different travel path when hitting one of the paddles
    - render: telling what color each pixel needs
    - score_render: telling which pixels should be colored for displaying the score
    - VGA_sync: cycling through each pixel per frame
    - tt_um_neuropong: linking inputs/outputs between internal modules


## How to test

For the input you need to connect two buttons to the VCC on the demo board and with input 0 (left paddle up) and input 1 (left paddle down). 
With the use of a Tiny VGA Pmod you can connect the output of the demo board to a VGA screen(640x480).

Furthermore supply a clock signal of 25.175 MHz.

## External hardware

- Tiny VGA Pmod
- VGA display (640x480)
- Two push buttons
