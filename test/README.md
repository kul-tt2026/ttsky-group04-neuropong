# Sample Testbench for a Tiny Tapeout Project

This is a sample testbench for a Tiny Tapeout project. It uses [cocotb](https://docs.cocotb.org/en/stable/) to drive the DUT and check the outputs.
For more information, check the [Tiny Tapeout website](https://tinytapeout.com/hdl/testing/).

> **`test-neural-net` branch:** `tb.v` instantiates `neural_net` directly (instead of
> the full `tt_um_neuropong` chip via `project.v`), and `PROJECT_SOURCES` / `COCOTB_TEST_MODULES`
> in the `Makefile` point at `neural_net.v` / `test_neural_net.py` only. This lets
> `test_neural_net.py` drive and check the neural net's own top-level ports directly,
> without reaching into `project.v`'s internal instances (e.g. `dut.user_project.nn_inst`).
> `GATES=yes` does not apply here since the hardened netlist's top level is the full chip,
> not a standalone `neural_net`.

## Setting Up

1. Edit the [Makefile](Makefile) and modify `PROJECT_SOURCES` to point to your Verilog files.
2. Edit [tb.v](tb.v) and replace `tt_um_example` with your module name.

## Running Simulations

### RTL Simulation

```sh
make
```

### Gate-Level Simulation

First, harden your project and copy `../runs/wokwi/results/final/verilog/gl/{your_module_name}.v` to `gate_level_netlist.v`. Then run:

```sh
make GATES=yes
```

### VCD Waveform Format

By default, waveforms are saved in FST format. To use VCD format instead, edit `tb.v` to use `$dumpfile("tb.vcd");` and run:

```sh
make FST=
```

### Cleaning Build Artifacts

To remove all generated files (`sim_build/`, `__pycache__/`, `results.xml`, `tb.fst`):

```sh
make clean
```

## Viewing Waveforms

With [GTKWave](https://gtkwave.sourceforge.net/):

```sh
gtkwave tb.fst tb.gtkw
```

With [Surfer](https://surfer-project.org/):

```sh
surfer tb.fst
```
