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
    """Drive the neural net's own top-level inputs and pulse frame_tick for
    one clock edge, then report what the net decided (paddle_up / paddle_down).
    Only ports of neural_net itself are touched -- no internal signals."""
    dut.ball_y.value = ball_y
    dut.paddle_y.value = paddle_y
    dut.ball_dir_x.value = dir_x
    dut.ball_dir_y.value = dir_y

    dut.frame_tick.value = 1
    await RisingEdge(dut.clk)
    dut.frame_tick.value = 0
    await RisingEdge(dut.clk)

    return int(dut.paddle_up.value), int(dut.paddle_down.value)


def start_clock(dut):
    # Same 25.175 MHz / 60 FPS clock used by the full chip.
    clock = Clock(dut.clk, 39.72, unit="ns")
    cocotb.start_soon(clock.start())


@cocotb.test()
async def test_reset_state(dut):
    dut._log.info("Start neural net reset test")
    start_clock(dut)

    await reset_dut(dut)

    assert int(dut.paddle_up.value) == 0, "paddle_up must be 0 after reset"
    assert int(dut.paddle_down.value) == 0, "paddle_down must be 0 after reset"


@cocotb.test()
async def test_neural_net_drives_right_paddle(dut):
    """Reproduces the 'right paddle never moves' report: sweep the
    ball far above/below the paddle and check the neural net actually
    asserts paddle_up / paddle_down (it should, once past the dead zone)."""
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


@cocotb.test()
async def test_dead_zone_boundary(dut):
    """diff is compared strictly (> / <) against DEAD_ZONE=30, so +/-30
    itself must still be idle and +/-31 must already trigger movement."""
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


@cocotb.test()
async def test_paddle_only_updates_on_frame_tick(dut):
    """paddle_up/down must hold their value between frame ticks, even while
    ball_y/paddle_y keep changing on the wires in between."""
    dut._log.info("Start frame-tick gating test")
    start_clock(dut)

    await reset_dut(dut)

    paddle_y = 200
    up, down = await tick(dut, ball_y=paddle_y + 60, paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), "setup: expected paddle_down=1 before checking hold behaviour"

    # Change the inputs without pulsing frame_tick -- decision must not move.
    dut.ball_y.value = paddle_y - 60
    dut.ball_dir_y.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert int(dut.paddle_up.value) == 0, "paddle_up changed without a frame_tick"
        assert int(dut.paddle_down.value) == 1, "paddle_down should hold its value without a frame_tick"
