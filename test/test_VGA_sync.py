import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge


# PARAMETERS
H_DISPLAY = 640
H_FRONT_PORCH = 16
H_SYNC = 96
H_BACK_PORCH = 48
H_TOTAL = H_DISPLAY + H_FRONT_PORCH + H_SYNC + H_BACK_PORCH  # 800 cycles

V_DISPLAY = 480
V_FRONT_PORCH = 10
V_SYNC = 2
V_BACK_PORCH = 33
V_TOTAL = V_DISPLAY + V_FRONT_PORCH + V_SYNC + V_BACK_PORCH  # 525 lines



async def reset_dut(dut):
    dut.reset.value = 1
    await ClockCycles(dut.clk, 10)
    dut.reset.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_VGA_sync(dut):
    dut._log.info("Start")

    clock = Clock(dut.clk, 39.72, unit="ns") # 25.175 MHz ==> 60 FPS
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    assert (dut.h_count.value == 0), f"Expect h_count=0 , but is {dut.h_count.value}"
    assert (dut.v_count.value == 0), f"Expect v_count=0 , but is {dut.v_count.value}"

    assert (dut.draw_enable.value == 1), "draw_enable must be high at (0,0)"

    assert (dut.hsync.value == 1), "hsync is active-low, must be one on display"
    assert (dut.vsync.value == 1), "vsync is active-low, must be one on display"

    # Assertions on one horizontal length
    for h in range(H_TOTAL):
        assert (dut.h_count.value == h), f"h_count mismatch with {h}"

        expected_draw = 1 if (h< H_DISPLAY) else 0
        assert (dut.draw_enable.value == expected_draw), f"draw_enable error at h={h}"

        is_hsync_active = ((H_DISPLAY + H_FRONT_PORCH) <= h < (H_DISPLAY + H_FRONT_PORCH + H_SYNC))
        expected_hsync = 0 if is_hsync_active else 1
        assert (dut.hsync.value == expected_hsync), f"hsync signal error on h={h}" 

        await RisingEdge(dut.clk)

    assert (dut.h_count.value == 0), "h_count is not reset after a full horizontal length"
    assert (dut.v_count.value == 1), "v_count is not summed with one"

    await ClockCycles(dut.clk, (V_TOTAL - 1) * H_TOTAL)

    assert ( dut.h_count.value == 0), "h_count must be reset after one frame"
    assert ( dut.v_count.value == 0), "v_count must be reset after one frame"




