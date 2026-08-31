# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

H_DISPLAY = 640
V_DISPLAY = 480
H_TOTAL = 800
V_TOTAL = 525
FRAME_CYCLES = H_TOTAL * V_TOTAL  # one full VGA_sync

X = 15
L_PADDLE_X = 2 * X                # 30
R_PADDLE_X = H_DISPLAY - 3 * X    # 595
PADDLE_HEIGHT = 5 * X             # 75

# 7-segment score digit locations 
SCORE_SEG = {
    "l": {"A": (260, 32), "D": (260, 77), "G": (260, 54)},
    "r": {"A": (370, 32), "D": (370, 77), "G": (370, 54)},
}

WHITE = (0b11, 0b11, 0b11)   # ball
RED = (0b11, 0b00, 0b00)     # left paddle
BLUE = (0b00, 0b00, 0b11)    # right paddle
BLACK = (0b00, 0b00, 0b00)   # background
GRAY = (0b10, 0b10, 0b10)    # score digit segment


class VGACursor:
    """Tracks how many clock edges have elapsed since h_count/v_count were
    last known to be (0, 0), so we can compute pixel timing purely from the
    clock -- without reading VGA_sync's internal counters. This is what
    makes these tests work identically in RTL and gate-level simulation."""

    def __init__(self, cycle):
        self.cycle = cycle % FRAME_CYCLES


async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    # cycle still zero because color is always one cycle after h_count
    return VGACursor(cycle=0)


async def get_output(dut):
    uo = dut.uo_out.value
    # bit mapping: putting 2 bits of each color back together
    red = (int(uo[0]) << 1) | int(uo[4])
    green = (int(uo[1]) << 1) | int(uo[5])
    blue = (int(uo[2]) << 1) | int(uo[6])

    hsync = int(uo[7])
    vsync = int(uo[3])

    return red, green, blue, hsync, vsync


async def wait_frame_tick(dut, cursor):
    await ClockCycles(dut.clk, FRAME_CYCLES)
    cursor.cycle = (cursor.cycle + FRAME_CYCLES) % FRAME_CYCLES


async def advance_edges(dut, cursor, n):
    await ClockCycles(dut.clk, n)
    cursor.cycle = (cursor.cycle + n) % FRAME_CYCLES


async def sample_pixel(dut, cursor, target_h, target_v):
    target_cycle = target_v * H_TOTAL + target_h
    delta = (target_cycle - cursor.cycle) % FRAME_CYCLES
    if delta:
        await ClockCycles(dut.clk, delta)
        cursor.cycle = (cursor.cycle + delta) % FRAME_CYCLES

    await RisingEdge(dut.clk)  # let render's registered color catch up
    cursor.cycle = (cursor.cycle + 1) % FRAME_CYCLES

    red, green, blue, _, _ = await get_output(dut)
    return red, green, blue


async def assert_scores_zero(dut, cursor):
    
    checks = [
        ("l", "A", True), ("r", "A", True),
        ("l", "G", False), ("r", "G", False),
        ("l", "D", True), ("r", "D", True),
    ]
    for side, seg, expected_on in checks:
        h, v = SCORE_SEG[side][seg]
        color = await sample_pixel(dut, cursor, h, v)
        is_on = color == GRAY
        if expected_on:
            assert is_on, (
                f"{side}_score segment {seg} should be lit for score=0, got {color}"
            )
        else:
            assert not is_on, (
                f"{side}_score segment {seg} should be OFF for score=0, got {color}"
            )


def start_clock(dut):
    # Set the clock period to 39.72 ns (25.175 MHz) ==> 60 FPS
    clock = Clock(dut.clk, 39.72, unit="ns")
    cocotb.start_soon(clock.start())


@cocotb.test()
async def test_reset_state(dut):
    dut._log.info("Start reset test")
    start_clock(dut)
    cursor = await reset_dut(dut)

    await assert_scores_zero(dut, cursor)
    
    color = await sample_pixel(dut, cursor, H_DISPLAY // 2 - (X//2), V_DISPLAY // 2 - (X//2))
    assert color == WHITE, f"Ball's top-left corner must be at ({H_DISPLAY // 2 - (X//2)},{V_DISPLAY // 2 - (X//2)})"

    
    color = await sample_pixel(dut, cursor, H_DISPLAY // 2, V_DISPLAY // 2)
    assert color == WHITE, f"Ball must be centered after reset, got {color}"


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
    assert hsync == 1, "hsync must be 1 outside of sync pulse"
    assert vsync == 1, "vsync must be 1 outside of sync pulse"


@cocotb.test()
async def test_color_bit_mapping(dut):
    dut._log.info("Start color bit mapping test")
    start_clock(dut)
    cursor = await reset_dut(dut)

    # Background -> black (v=50, checked first)
    color = await sample_pixel(dut, cursor, 50, 50)
    assert color == BLACK, f"Background pixel should be black, got {color}"

    # Ball -> white (all channels max) (v=247)
    color = await sample_pixel(dut, cursor, H_DISPLAY // 2, V_DISPLAY // 2)
    assert color == WHITE, f"Ball pixel should be white, got {color}"

    # Left paddle -> pure red (v=250, h=35)
    color = await sample_pixel(dut, cursor, L_PADDLE_X + 5, V_DISPLAY // 2 - 3*X//2 + 10)
    assert color == RED, f"Left paddle pixel should be pure red, got {color}"

    # Right paddle -> pure blue (v=250, h=600 -- same row, higher h)
    color = await sample_pixel(dut, cursor, R_PADDLE_X + 5, V_DISPLAY // 2 - 3*X//2 + 10)
    assert color == BLUE, f"Right paddle pixel should be pure blue, got {color}"


@cocotb.test()
async def test_left_paddle_movement(dut):
    dut._log.info("Start left paddle movement test")
    start_clock(dut)
    cursor = await reset_dut(dut)

    # Top edge of the paddle's initial box: [V_DISPLAY/2 , V_DISPLAY/2 + PADDLE_HEIGHT)
    top_h, top_v = L_PADDLE_X, V_DISPLAY // 2 - 3*X//2

    color = await sample_pixel(dut, cursor, top_h, top_v)
    assert color == RED, f"Expected left paddle at its initial top edge, got {color}"

    dut.ui_in.value = 0b0000_0010  # move left paddle down
    await wait_frame_tick(dut, cursor)

    color = await sample_pixel(dut, cursor, top_h, top_v)
    assert color != RED, f"Left paddle should have moved down, old top row is still {color}"


@cocotb.test()
async def test_game_reset(dut):
    dut._log.info("Start game reset test")
    start_clock(dut)
    cursor = await reset_dut(dut)

    await assert_scores_zero(dut, cursor)

    top_h, top_v = L_PADDLE_X, V_DISPLAY // 2 - 3*X//2

    dut.ui_in.value = 0b0000_0010  # move left paddle down
    await wait_frame_tick(dut, cursor)

    color = await sample_pixel(dut, cursor, top_h, top_v)
    assert color != RED, "Left paddle should have moved away from its top row before reset"

    dut.ui_in.value = 0b0001_0000  # game reset
    await advance_edges(dut, cursor, 2)
    dut.ui_in.value = 0  # release the button so nothing keeps drifting

    color = await sample_pixel(dut, cursor, H_DISPLAY // 2, V_DISPLAY // 2)
    assert color == WHITE, f"Ball should have reset to its centered position, got {color}"

    color = await sample_pixel(dut, cursor, top_h, top_v)
    assert color == RED, f"Left paddle should have reset to its centered position, got {color}"

"""Takes too long"""
# @cocotb.test()
# async def test_right_paddle_neural_net(dut):
#     dut._log.info("Start right paddle neural net test")
#     start_clock(dut)
#     cursor = await reset_dut(dut)

#     h = R_PADDLE_X + 5
#     top_v = V_DISPLAY // 2
#     bot_v = V_DISPLAY // 2 + PADDLE_HEIGHT - 1

#     top_before = await sample_pixel(dut, cursor, h, top_v)
#     bot_before = await sample_pixel(dut, cursor, h, bot_v)
#     assert top_before == BLUE, f"Expected right paddle at its top edge, got {top_before}"
#     assert bot_before == BLUE, f"Expected right paddle at its bottom edge, got {bot_before}"

#     pong = dut.user_project.pong_inst
#     for number in range(20):
#         await wait_frame_tick(dut, cursor)
#         dut._log.info(f"{number}: {pong.r_paddle_y.value}")

    

#     top_after = await sample_pixel(dut, cursor, h, top_v)
#     bot_after = await sample_pixel(dut, cursor, h, bot_v)


#     # A downward move clears the top row; an upward move clears the bottom
#     # row -- checking both edges catches movement in either direction.
#     assert top_after != BLUE or bot_after != BLUE, (
#         "Right paddle should have moved (neither edge changed color), but appears stationary"
#     )