import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

async def reset_dut(dut):
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def set_vga_and_tick(dut, h, v):
    # Set h_count and v_count
    render_inst = dut.user_project.render_inst
    render_inst.h_count.value = h
    render_inst.v_count.value = v

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_render_logic(dut):
    dut._log.info("Start RENDER test")

    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    render_inst = dut.user_project.render_inst

    render_inst.draw_enable.value = 1
    render_inst.l_paddle_y.value = 100
    render_inst.r_paddle_y.value = 100
    render_inst.ball_x.value = 200
    render_inst.ball_y.value = 200
    render_inst.l_score.value = 0
    render_inst.r_score.value = 0

    # no draw_enable ==> black
    render_inst.draw_enable.value = 0
    await set_vga_and_tick(dut, 200, 200)

    assert render_inst.red.value == 0, "R must be 0 when draw_enable=0"
    assert render_inst.green.value == 0, "G must be 0 when draw_enable=0"
    assert render_inst.blue.value == 0, "B must be 0 when draw_enable=0"

    render_inst.draw_enable.value = 1

    #black background on (10,10)
    await set_vga_and_tick(dut, 10, 10)

    assert render_inst.red.value == 0b00, f"Background R must be 00, got {render_inst.red.value}"
    assert render_inst.green.value == 0b00, f"Background G must be 00, got {render_inst.green.value}"
    assert render_inst.blue.value == 0b00, f"Background B must be 00, got {render_inst.blue.value}"

    # ball on (200,200) ==> White 
    await set_vga_and_tick(dut, 200, 200)

    assert render_inst.red.value == 0b11, f"Ball R must be 11, got {render_inst.red.value}"
    assert render_inst.green.value == 0b11, f"Ball G must be 11, got {render_inst.green.value}"
    assert render_inst.blue.value == 0b11, f"Ball B must be 11, got {render_inst.blue.value}"

    # left paddle on (35,105) ==> Red
    await set_vga_and_tick(dut, 35, 105)

    assert render_inst.red.value == 0b11, f"Left paddle R must be 11, got {render_inst.red.value}"
    assert render_inst.green.value == 0b00, f"Left paddle G must be 00, got {render_inst.green.value}"
    assert render_inst.blue.value == 0b00, f"Left paddle B must be 00, got {render_inst.blue.value}"

    # right paddle on (600,105) ==> Blue
    await set_vga_and_tick(dut, 600, 105)

    assert render_inst.red.value == 0b00, f"Right paddle R must be 00, got {render_inst.red.value}"
    assert render_inst.green.value == 0b00, f"Right paddle G must be 00, got {render_inst.green.value}"
    assert render_inst.blue.value == 0b11, f"Right paddle B must be 11, got {render_inst.blue.value}"