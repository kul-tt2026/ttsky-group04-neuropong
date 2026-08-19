# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

H_DISPLAY = 640
V_DISPLAY = 480
H_TOTAL = 800
V_TOTAL = 525
X = 15

async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def get_output(dut):
    uo = dut.uo_out.value
    # bit mapping: putting 2 bits of each color back together
    red = (int(uo[0]) << 1) | int(uo[4])
    green = (int(uo[1]) << 1) | int(uo[5])
    blue = (int(uo[2]) << 1) | int(uo[6])

    hsync = int(uo[7])
    vsync = int(uo[3])

    return red, green, blue, hsync, vsync

async def wait_frame_tick(dut):
    await ClockCycles(dut.clk, H_TOTAL * V_TOTAL)  # Wait for one frame tick

def start_clock(dut):
    # Set the clock period to 39.72 ns (25.175 MHz) ==> 60 FPS
    clock = Clock(dut.clk, 39.72, unit="ns")
    cocotb.start_soon(clock.start())


@cocotb.test()
async def test_reset_state(dut):

    dut._log.info("Start reset test")
    start_clock(dut)

    await reset_dut(dut)

    pong = dut.user_project.pong_inst
    assert pong.l_score.value == 0, f"l_score must be 0 after reset, got {pong.l_score.value}"
    assert pong.r_score.value == 0, f"r_score must be 0 after reset, got {pong.r_score.value}"
    assert pong.ball_x.value == H_DISPLAY // 2 - X // 2, f"ball_x must be {H_DISPLAY // 2 - X // 2} after reset, got {pong.ball_x.value}"
    assert pong.ball_y.value == V_DISPLAY // 2 - X // 2, f"ball_y must be {V_DISPLAY // 2 - X // 2} after reset, got {pong.ball_y.value}"

@cocotb.test()
async def test_no_unknown_outputs(dut):
    dut._log.info("Start unknown outputs test")
    start_clock(dut)

    await reset_dut(dut)


    # Each output must always have values of 0 or 1
    for _ in range(2000):
        await RisingEdge(dut.clk)
        assert dut.uo_out.value.is_resolvable, f"uo_out has unknown value: {dut.uo_out.value}"

@cocotb.test()
async def test_hsync_vsync(dut):
    dut._log.info("Start hsync/vsync test")
    start_clock(dut)

    await reset_dut(dut)
    await RisingEdge(dut.clk)

    _, _, _, hsync, vsync = await get_output(dut)
    assert hsync == 1, f"hsync must be 1 outside of sync pulse"
    assert vsync == 1, f"vsync must be 1 outside of sync pulse"

@cocotb.test()
async def test_color_bit_mapping(dut):
    start_clock(dut)

    await reset_dut(dut)

    # Check that the color bits are correctly mapped to the output
    render_inst = dut.user_project.render_inst
    
    render_inst.red.value = 0b10
    render_inst.green.value = 0b01
    render_inst.blue.value = 0b11
    await RisingEdge(dut.clk)

    red, green, blue, _, _ = await get_output(dut)
    assert red == 0b10, f"Red bit mapping error: expected 0b10, got {red}"
    assert green == 0b01, f"Green bit mapping error: expected 0b01, got {green}"
    assert blue == 0b11, f"Blue bit mapping error: expected 0b11, got {blue}"

@cocotb.test()
async def test_left_paddle_movement(dut):
    dut._log.info("Start left paddle movement test")
    start_clock(dut)

    await reset_dut(dut)

    pong = dut.user_project.pong_inst
    start_y = int(pong.l_paddle_y.value)

    assert start_y == V_DISPLAY // 2 - (3*X // 2), f"Left paddle initial position must be {V_DISPLAY // 2 - (3*X // 2)}, got {start_y}"

    dut.ui_in.value = 0b0000_0010 # move left paddle down
    await wait_frame_tick(dut)

    assert int(pong.l_paddle_y.value) > start_y, f"Left paddle should have moved down, but is at {pong.l_paddle_y.value}"

@cocotb.test()
async def test_game_reset(dut):
    dut._log.info("Start game reset test")
    start_clock(dut)

    await reset_dut(dut)

    pong = dut.user_project.pong_inst
    dut.ui_in.value = 0b0000_0010 # move left paddle down
    await wait_frame_tick(dut)
    assert int(pong.l_paddle_y.value) != V_DISPLAY // 2 - (3*X // 2), f"Left paddle should have moved down, but is at {pong.l_paddle_y.value}"

    dut.ui_in.value = 0b0001_0000 # game reset
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    assert int(pong.l_paddle_y.value) == V_DISPLAY // 2 - (3*X // 2), f"Left paddle should have reset to {V_DISPLAY // 2 - (3*X // 2)}, but is at {pong.l_paddle_y.value}"
    assert int(pong.l_score.value) == 0, f"Left score should have reset to 0, but is at {pong.l_score.value}"
    assert int(pong.r_score.value) == 0, f"Right score should have reset to 0, but is at {pong.r_score.value}"

@cocotb.test()
async def test_right_paddle_neural_net(dut):
    dut._log.info("Start right paddle neural net test")
    start_clock(dut)

    await reset_dut(dut)

    pong = dut.user_project.pong_inst
    start_y = int(pong.r_paddle_y.value)

    assert start_y == V_DISPLAY // 2 - (3*X // 2), f"Right paddle initial position must be {V_DISPLAY // 2 - (3*X // 2)}, got {start_y}"
    pong.ball_x.value = 570
    pong.ball_y.value = 440
    for _ in range(5):
        await wait_frame_tick(dut)

    end_y = int(pong.r_paddle_y.value)
    assert end_y != start_y, f"Right paddle should have moved, but is still at {pong.r_paddle_y.value}"
    dut._log.info(f"{pong.r_paddle_y.value}")