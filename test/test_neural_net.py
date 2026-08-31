import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


async def reset_dut(dut):
    dut.reset_n.value = 0
    dut.frame_tick.value = 0
    dut.ball_y.value = 0
    dut.ball_dir_x.value = 0
    dut.ball_dir_y.value = 0
    dut.paddle_y.value = 0
    await ClockCycles(dut.clk, 10)
    dut.reset_n.value = 1
    await RisingEdge(dut.clk)


async def tick(dut, ball_y, paddle_y, dir_x, dir_y):
    """Set the ball and paddle values, pulse frame_tick for one clock edge,
    then wait and return what the net decided (paddle_up, paddle_down).

    The net takes a few clock cycles to work through its sequential stages before the
    decision shows up on the outputs, so we wait a bit longer than one
    cycle before reading the result."""
    dut.ball_y.value = ball_y
    dut.paddle_y.value = paddle_y
    dut.ball_dir_x.value = dir_x
    dut.ball_dir_y.value = dir_y

    dut.frame_tick.value = 1
    await RisingEdge(dut.clk)
    dut.frame_tick.value = 0
    await ClockCycles(dut.clk, 3)

    return int(dut.paddle_up.value), int(dut.paddle_down.value)


def start_clock(dut):
    # Same clock speed the real chip runs at (25.175 MHz, 60 FPS).
    clock = Clock(dut.clk, 39.72, unit="ns")
    cocotb.start_soon(clock.start())


# Right after reset, the paddle should not be told to move at all.
@cocotb.test()
async def test_reset_state(dut):
    dut._log.info("Start neural net reset test")
    start_clock(dut)

    await reset_dut(dut)

    assert int(dut.paddle_up.value) == 0, "paddle_up must be 0 after reset"
    assert int(dut.paddle_down.value) == 0, "paddle_down must be 0 after reset"


# Put the ball far above and far below the paddle and check the net
# actually tells the paddle to move, not just stay idle. Opposite test of previous one.
@cocotb.test()
async def test_neural_net_drives_right_paddle(dut):
    dut._log.info("Start neural net test")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 240

    # Ball well below paddle -> net should say "move down"
    up, down = await tick(dut, ball_y=paddle_y + 60, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), f"expected paddle_down=1 when ball is far below, got up={up} down={down}"

    # Ball well above paddle -> net should say "move up"
    up, down = await tick(dut, ball_y=paddle_y - 60, paddle_y=paddle_y, dir_x=0, dir_y=1)
    assert (up, down) == (1, 0), f"expected paddle_up=1 when ball is far above, got up={up} down={down}"

    # Ball aligned with paddle (inside the +/-30 dead zone) -> net should be idle
    up, down = await tick(dut, ball_y=paddle_y, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 0), f"expected no movement inside dead zone, got up={up} down={down}"


# Testing the dead zone at its boundaries
@cocotb.test()
async def test_dead_zone_boundary(dut):
    dut._log.info("Start dead zone boundary test")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 300

    up, down = await tick(dut, ball_y=paddle_y + 30, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 0), f"expected idle exactly at +DEAD_ZONE, got up={up} down={down}"

    up, down = await tick(dut, ball_y=paddle_y + 31, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), f"expected paddle_down=1 just past +DEAD_ZONE, got up={up} down={down}"

    up, down = await tick(dut, ball_y=paddle_y - 30, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 0), f"expected idle exactly at -DEAD_ZONE, got up={up} down={down}"

    up, down = await tick(dut, ball_y=paddle_y - 31, paddle_y=paddle_y, dir_x=0, dir_y=1)
    assert (up, down) == (1, 0), f"expected paddle_up=1 just past -DEAD_ZONE, got up={up} down={down}"


# The outputs should only change on a frame tick
@cocotb.test()
async def test_paddle_only_updates_on_frame_tick(dut):
    dut._log.info("Start frame-tick gating test")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 200
    up, down = await tick(dut, ball_y=paddle_y + 60, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), "setup: expected paddle_down=1 before checking hold behaviour"

    # Change the inputs without pulsing frame_tick, the outputs should not move.
    dut.ball_y.value = paddle_y - 60
    dut.ball_dir_y.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert int(dut.paddle_up.value) == 0, "paddle_up changed without a frame_tick"
        assert int(dut.paddle_down.value) == 1, "paddle_down should hold its value without a frame_tick"


# Check the neural network output (in extreme conditions) with only ball position, not direction
@cocotb.test()
async def test_decision_ignores_ball_direction_outside_dead_zone(dut):
    dut._log.info("Start direction-independence test (outside dead zone)")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 260

    for dir_x in (0, 1):
        for dir_y in (0, 1):
            up, down = await tick(dut, ball_y=paddle_y + 100, paddle_y=paddle_y, dir_x=dir_x, dir_y=dir_y)
            assert (up, down) == (0, 1), (
                f"ball far below should always give paddle_down=1 regardless of direction, "
                f"got up={up} down={down} for dir_x={dir_x} dir_y={dir_y}"
            )

    for dir_x in (0, 1):
        for dir_y in (0, 1):
            up, down = await tick(dut, ball_y=paddle_y - 100, paddle_y=paddle_y, dir_x=dir_x, dir_y=dir_y)
            assert (up, down) == (1, 0), (
                f"ball far above should always give paddle_up=1 regardless of direction, "
                f"got up={up} down={down} for dir_x={dir_x} dir_y={dir_y}"
            )


# Same idea as above, but with the ball lined up with the paddle
# No matter which direction the ball is heading, the net should stay idle
@cocotb.test()
async def test_dead_zone_holds_regardless_of_ball_direction(dut):
    dut._log.info("Start direction-independence test (inside dead zone)")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 150

    for dir_x in (0, 1):
        for dir_y in (0, 1):
            up, down = await tick(dut, ball_y=paddle_y, paddle_y=paddle_y, dir_x=dir_x, dir_y=dir_y)
            assert (up, down) == (0, 0), (
                f"aligned ball should stay idle regardless of direction, "
                f"got up={up} down={down} for dir_x={dir_x} dir_y={dir_y}"
            )


# paddle_up and paddle_down should never both be on at once
@cocotb.test()
async def test_outputs_are_mutually_exclusive(dut):
    dut._log.info("Start mutual-exclusivity sweep")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 400
    offsets = (-500, -100, -60, -31, -30, -1, 0, 1, 30, 31, 60, 100, 500)

    for offset in offsets:
        for dir_x in (0, 1):
            for dir_y in (0, 1):
                ball_y = max(0, min(1023, paddle_y + offset))
                up, down = await tick(dut, ball_y=ball_y, paddle_y=paddle_y, dir_x=dir_x, dir_y=dir_y)
                assert not (up and down), (
                    f"paddle_up and paddle_down both asserted for ball_y={ball_y} "
                    f"paddle_y={paddle_y} dir_x={dir_x} dir_y={dir_y}"
                )


# Check the net output at extreme ranges for the ball and paddle (at the edge of the screen).
@cocotb.test()
async def test_extreme_input_range(dut):
    dut._log.info("Start extreme input range test")
    start_clock(dut)

    await reset_dut(dut)

    up, down = await tick(dut, ball_y=1023, paddle_y=0, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), f"expected paddle_down=1 at maximum positive diff, got up={up} down={down}"

    up, down = await tick(dut, ball_y=0, paddle_y=1023, dir_x=0, dir_y=1)
    assert (up, down) == (1, 0), f"expected paddle_up=1 at maximum negative diff, got up={up} down={down}"
