import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


async def reset_dut(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def tick(dut, sync_inst, nn_inst, ball_y, paddle_y, dir_x, dir_y):
    """Force the neural net's inputs and pulse frame_tick for one frame,
    then report what the net decided (nn_paddle_up / nn_paddle_down)."""
    nn_inst.ball_y.value = ball_y
    nn_inst.paddle_y.value = paddle_y
    nn_inst.ball_dir_x.value = dir_x
    nn_inst.ball_dir_y.value = dir_y

    # frame_tick is a wire driven by VGA_sync; force it directly for a
    # single clock edge so we don't have to wait out a full VGA frame.
    sync_inst.frame_tick.value = 1
    await RisingEdge(dut.clk)
    sync_inst.frame_tick.value = 0
    await RisingEdge(dut.clk)

    return int(nn_inst.paddle_up.value), int(nn_inst.paddle_down.value)


@cocotb.test()
async def test_neural_net_drives_right_paddle(dut):
    """Reproduces the 'right paddle never moves' report: sweep the
    ball far above/below the paddle and check the neural net actually
    asserts paddle_up / paddle_down (it should, once past the dead zone)."""
    dut._log.info("Start neural net test")

    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    sync_inst = dut.user_project.sync_inst
    nn_inst = dut.user_project.nn_inst

    paddle_y = 240

    # Ball well below paddle -> net should say "move down"
    up, down = await tick(dut, sync_inst, nn_inst, ball_y=paddle_y + 60,
                           paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 1), f"expected paddle_down=1 when ball is far below, got up={up} down={down}"

    # Ball well above paddle -> net should say "move up"
    up, down = await tick(dut, sync_inst, nn_inst, ball_y=paddle_y - 60,
                           paddle_y=paddle_y, dir_x=0, dir_y=1)
    assert (up, down) == (1, 0), f"expected paddle_up=1 when ball is far above, got up={up} down={down}"

    # Ball aligned with paddle (inside the +/-30 dead zone) -> net should be idle
    up, down = await tick(dut, sync_inst, nn_inst, ball_y=paddle_y,
                           paddle_y=paddle_y, dir_x=0, dir_y=0)
    assert (up, down) == (0, 0), f"expected no movement inside dead zone, got up={up} down={down}"