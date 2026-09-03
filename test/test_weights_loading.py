"""
Cocotb testbench: test enkel het inladen (scannen) van nieuwe gewichten
in de neural_net-instantie, via de top-level poorten van tt_um_neuropong
(ui_in[6] = weight_load, ui_in[7] = weight_in).

Interne signalen (dut.nn_inst.weight_shift) worden rechtstreeks via
hierarchische paden gelezen/geverifieerd -- dit kan alleen in simulatie,
niet op de echte silicon chip.

DUT: tt_um_neuropong (project.v)
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer

W_HID_BITS = 48
W_OUT_BITS = 32
W_BITS = W_HID_BITS + W_OUT_BITS  # 80

WP = 0b01  # +1
WZ = 0b00  #  0
WN = 0b10  # -1

async def start_clock(dut):
    cocotb.start_soon(
        Clock(dut.clk, 39.72, unit="ns").start()
    )
    await Timer(1, unit="ns")

def default_weight_vector():
    """Herbouwt de hardgecodeerde reset-waarde uit neural_net.v (regel 43-56)."""
    hidden = [
        (WZ, WN, WP), (WZ, WN, WP),
        (WZ, WZ, WP), (WZ, WZ, WP),
        (WZ, WZ, WP), (WZ, WZ, WP),
        (WZ, WZ, WP), (WZ, WZ, WP),
    ]
    out0 = (WP,) * 8   # paddle_up
    out1 = (WN,) * 8   # paddle_down

    codes = [c for triplet in hidden for c in triplet] + list(out0) + list(out1)

    value = 0
    for code in codes:  # eerste element = meest significante bits (MSB-first)
        value = (value << 2) | code
    return value


def random_weight_vector():
    """Willekeurige testvector van 80 bits (40 geldige ternaire codes)."""
    codes = [random.choice([WP, WZ, WN]) for _ in range(40)]
    value = 0
    for code in codes:
        value = (value << 2) | code
    return value


async def reset_chip(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def shift_in_weights(dut, value, n_bits=W_BITS):
    """Schuift value MSB-first in via weight_load/weight_in."""
    for i in range(n_bits - 1, -1, -1):
        bit = (value >> i) & 1

        # Zet de ingang ruim vóór de klokflank
        dut.ui_in.value = (bit << 7) | (1 << 6)

        # Wacht tot de signalen daadwerkelijk stabiel zijn
        await Timer(1, unit="ns")

        # Laat Verilog de bit samplen
        await RisingEdge(dut.clk)

    # Wacht tot de laatste kloktransactie volledig verwerkt is
    await Timer(1, unit="ns")

    # weight_load en weight_in laag
    dut.ui_in.value = 0

    # Zorg dat deze wijziging niet met een klokflank racet
    await Timer(1, unit="ns")


@cocotb.test()
async def test_default_weights_after_reset(dut):
    """Na reset moeten de gewichten exact de hardgecodeerde default-waarde zijn."""
    await start_clock(dut)
    await reset_chip(dut)

    expected = default_weight_vector()
    actual = int(dut.user_project.nn_inst.weight_shift.value)

    assert actual == expected, (
        f"Default weights kloppen niet na reset: "
        f"verwacht {expected:#022x}, gekregen {actual:#022x}"
    )


@cocotb.test()
async def test_weight_scan_in(dut):
    """Nieuwe, willekeurige gewichtenvector inschuiven en verifiëren dat hij
    exact zo in weight_shift terechtkomt."""
    await start_clock(dut)
    await reset_chip(dut)

    new_weights = random_weight_vector()
    await shift_in_weights(dut, new_weights)

    actual = int(dut.user_project.nn_inst.weight_shift.value)
    assert actual == new_weights, (
        f"Ingeschoven gewichten kloppen niet: "
        f"verwacht {new_weights:#022x}, gekregen {actual:#022x}"
    )


@cocotb.test()
async def test_weight_load_deasserted_holds_value(dut):
    """Zolang weight_load laag is, mag weight_shift niet meer veranderen,
    ook al blijft de chip gewoon doorklokken."""
    await start_clock(dut)
    await reset_chip(dut)

    new_weights = random_weight_vector()
    await shift_in_weights(dut, new_weights)
    value_after_load = int(dut.user_project.nn_inst.weight_shift.value)

    dut.ui_in.value = 0  # weight_load blijft laag
    await ClockCycles(dut.clk, 20)

    value_after_idle = int(dut.user_project.nn_inst.weight_shift.value)
    assert value_after_idle == value_after_load, (
        "weight_shift veranderde terwijl weight_load laag stond!"
    )