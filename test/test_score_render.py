import cocotb
from cocotb.triggers import Timer

SEG_PATTERNS = {
    0: 0b1111110,
    1: 0b0110000,
    2: 0b1101101,
    3: 0b1111001,
    4: 0b0110011,
    5: 0b1011011,
    6: 0b1011111,
    7: 0b1110000,
    8: 0b1111111,
    9: 0b1111011,
}

@cocotb.test()
async def test_score_render_logic(dut):

    dut._log.info("Start SCORE_RENDER")

    score_inst = dut.user_project.render_inst.score_inst

    score_inst.l_score.value = 3
    score_inst.r_score.value = 8

    score_inst.h_count.value = 10
    score_inst.v_count.value = 10
    await Timer(1, unit="ns")
    assert score_inst.draw_score.value == 0, f"Error: draw_score must be 0 at (10,10)"

    score_inst.h_count.value = 260
    score_inst.v_count.value = 32
    await Timer(1, unit="ns")
    assert score_inst.draw_score.value == 1, f"Error: draw_score must be 1 at Segment A for l_score = 3"

    score_inst.h_count.value = 252
    score_inst.v_count.value = 40
    await Timer(1, unit="ns")
    assert score_inst.draw_score.value == 0, f"Error: draw_score must be 0 at Segment F for l_score = 3"

    score_inst.h_count.value = 370
    score_inst.v_count.value = 55
    await Timer(1, unit="ns")
    assert score_inst.draw_score.value == 1, f"Error: draw_score must be 1 at Segment G for r_score = 8"
