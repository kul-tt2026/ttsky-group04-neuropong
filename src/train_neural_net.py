"""
PyTorch training script for the ternary neural net in neural_net.v.

The chip's weights are no longer frozen at hardening: neural_net.v now holds
W_HID/W_OUT in a shift register (weight_load/weight_in) instead of a
`parameter`, so a freshly trained weight set can be shifted into the real
silicon after tapeout. This script produces that weight set.

Network shape mirrors neural_net.v exactly:
    N_IN  = 3   (t_diff, t_dir_y, t_dir_x)
    N_HID = 8   ternary hidden neurons, thresholds fixed at +-1
    N_OUT = 2   {paddle_up, paddle_down}, threshold fixed at 4

Only the weights are trained. The thresholds (TH_HID_POS/TH_HID_NEG/TH_OUT)
are hardware constants, so they are baked into the forward pass exactly like
the HDL instead of being learned.

Training data comes from pong_hdl.PongLogic, the bit-accurate model of the
HDL game, so the input features are guaranteed to match what neural_net.v
actually sees on ball_y/ball_dir_x/ball_dir_y/paddle_y.

The output is a trained ternary weight vector, printed both as Verilog
parameter blocks (for reference) and as the MSB-first bitstream to drive
into weight_in while holding weight_load high, matching the layout that
neural_net.v's reset value uses.
"""

import random
from dataclasses import dataclass
from typing import List, Tuple

import torch
import torch.nn as nn

from pong_hdl import PongLogic, make_training_input


# ---------------------------------------------------------------------------
# Network shape, mirrors the parameters at the top of neural_net.v
# ---------------------------------------------------------------------------

N_IN = 3
N_HID = 8
N_OUT = 2

# Fixed neuron thresholds (signed), copied from neural_net.v. Not trained.
TH_HID_POS = 1
TH_HID_NEG = -1
TH_OUT = 4


# ---------------------------------------------------------------------------
# Straight-through estimators for the non-differentiable HDL operations
# ---------------------------------------------------------------------------
#
# neural_net.v only ever computes with {-1, 0, +1} weights/activations and
# hard thresholds, none of which have a useful gradient. Training instead
# keeps full-precision "shadow" tensors and snaps them to the HDL's discrete
# values on the forward pass, while letting the gradient flow straight
# through the snap on the backward pass (Straight-Through Estimator).

class TernarizeWeight(torch.autograd.Function):
    """Snap a real-valued weight to {-1, 0, +1}, same encoding as WP/WZ/WN."""

    THRESHOLD_FRACTION = 0.7  # fraction of mean(|w|) below which a weight is pruned to 0

    @staticmethod
    def forward(ctx, w_real):
        threshold = TernarizeWeight.THRESHOLD_FRACTION * w_real.abs().mean()
        w_tern = torch.zeros_like(w_real)
        w_tern[w_real > threshold] = 1.0
        w_tern[w_real < -threshold] = -1.0
        return w_tern

    @staticmethod
    def backward(ctx, grad_output):
        # Straight-through: pass the gradient on unchanged.
        return grad_output


class TernaryHiddenActivate(torch.autograd.Function):
    """assign hid[i] = (mac >= TH_HID_POS) ? 1 : (mac <= TH_HID_NEG) ? -1 : 0;"""

    @staticmethod
    def forward(ctx, mac):
        out = torch.zeros_like(mac)
        out[mac >= TH_HID_POS] = 1.0
        out[mac <= TH_HID_NEG] = -1.0
        return out

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output


class BinaryOutputActivate(torch.autograd.Function):
    """assign out[i] = (mac >= TH_OUT);"""

    @staticmethod
    def forward(ctx, mac):
        return (mac >= TH_OUT).float()

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output


def ternarize_weight(w_real: torch.Tensor) -> torch.Tensor:
    return TernarizeWeight.apply(w_real)


def hidden_activate(mac: torch.Tensor) -> torch.Tensor:
    return TernaryHiddenActivate.apply(mac)


def output_activate(mac: torch.Tensor) -> torch.Tensor:
    return BinaryOutputActivate.apply(mac)


# ---------------------------------------------------------------------------
# Network definition
# ---------------------------------------------------------------------------

class NeuralNetModel(nn.Module):
    """
    Same topology as neural_net.v: N_IN -> N_HID (ternary) -> N_OUT (binary).

    w_hid_real / w_out_real are full-precision shadow weights used only for
    training. Everything that actually runs (forward pass, and eventually
    the chip) uses the ternarized version of them.
    """

    def __init__(self):
        super().__init__()
        self.w_hid_real = nn.Parameter(torch.randn(N_HID, N_IN) * 0.5)
        self.w_out_real = nn.Parameter(torch.randn(N_OUT, N_HID) * 0.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, N_IN) with values in {-1, 0, +1}, same as in_vec in the HDL.
        w_hid = ternarize_weight(self.w_hid_real)
        w_out = ternarize_weight(self.w_out_real)

        hid_mac = x @ w_hid.t()               # (batch, N_HID)
        hid = hidden_activate(hid_mac)         # ternary hidden activations

        out_mac = hid @ w_out.t()              # (batch, N_OUT)
        out = output_activate(out_mac)         # {paddle_up, paddle_down}
        return out


# ---------------------------------------------------------------------------
# Training data, generated straight from the HDL-exact game model
# ---------------------------------------------------------------------------
#
# The oracle label follows the same dead-zone rule pong_hdl.py documents for
# neural_net.v: move toward the ball once it drifts far enough from the
# paddle, otherwise hold still. Self-play with a random opponent keeps the
# ball moving through the full range of ball_y/paddle_y combinations.

DEAD_ZONE = 30


@dataclass
class Example:
    features: Tuple[int, int, int]  # t_diff, t_dir_y, t_dir_x
    label: Tuple[int, int]          # paddle_up, paddle_down


def oracle_label(t_diff: int) -> Tuple[int, int]:
    if t_diff > 0:
        return (0, 1)  # ball below paddle -> move down
    elif t_diff < 0:
        return (1, 0)  # ball above paddle -> move up
    else:
        return (0, 0)  # inside the dead zone -> hold still


def generate_dataset(num_games: int = 200, frames_per_game: int = 300) -> List[Example]:
    """Play out random games with pong_hdl.PongLogic and record (features, label)
    pairs for the right paddle on every frame_tick."""

    rng = random.Random(0)
    examples: List[Example] = []

    for _ in range(num_games):
        game = PongLogic()

        for _ in range(frames_per_game):
            l_up = rng.random() < 0.5
            l_down = (not l_up) and rng.random() < 0.5
            r_up = rng.random() < 0.5
            r_down = (not r_up) and rng.random() < 0.5

            game.clock(
                frame_tick=True,
                l_paddle_up=l_up,
                l_paddle_down=l_down,
                r_paddle_up=r_up,
                r_paddle_down=r_down,
            )

            t_diff, t_dir_y, t_dir_x = make_training_input(game, paddle="right")
            examples.append(Example(
                features=(t_diff, t_dir_y, t_dir_x),
                label=oracle_label(t_diff),
            ))

    return examples


def to_tensors(examples: List[Example]) -> Tuple[torch.Tensor, torch.Tensor]:
    x = torch.tensor([e.features for e in examples], dtype=torch.float32)
    y = torch.tensor([e.label for e in examples], dtype=torch.float32)
    return x, y


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(model: NeuralNetModel, x: torch.Tensor, y: torch.Tensor,
          epochs: int = 200, lr: float = 0.1) -> None:
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    for epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(x)
        loss = loss_fn(pred, y)
        loss.backward()
        optimizer.step()

        if epoch % 20 == 0 or epoch == epochs - 1:
            accuracy = (pred.round() == y).all(dim=1).float().mean().item()
            print(f"epoch {epoch:4d}  loss {loss.item():.4f}  accuracy {accuracy:.4f}")


# ---------------------------------------------------------------------------
# Export trained weights in the layout neural_net.v expects
# ---------------------------------------------------------------------------
#
# neural_net.v's weight_shift reset value is, MSB first:
#   W_HID (neuron 0..7, each {w_dir_x, w_dir_y, w_diff})  then  W_OUT
# with each trit encoded as WP=01, WZ=00, WN=10 (see neural_net.v). This
# must match exactly, or the bits shifted into the chip will land on the
# wrong weight.

TRIT_CODE = {1: "01", 0: "00", -1: "10"}


def trit_bits(value: float) -> str:
    return TRIT_CODE[int(round(value))]


def export_weights(model: NeuralNetModel) -> str:
    w_hid = ternarize_weight(model.w_hid_real).detach().tolist()
    w_out = ternarize_weight(model.w_out_real).detach().tolist()

    bitstream = ""
    for neuron in w_hid:
        for w in neuron:
            bitstream += trit_bits(w)
    for neuron in w_out:
        for w in neuron:
            bitstream += trit_bits(w)

    lines = []
    lines.append("// Trained weights, MSB first, load with weight_load/weight_in:")
    lines.append(f"// {len(bitstream)}'b{bitstream}")
    lines.append("")
    lines.append("parameter [N_HID*N_IN*2-1:0] W_HID = {")
    for i, neuron in enumerate(w_hid):
        code = ", ".join(f"trit={int(round(w)):+d}" for w in neuron)
        lines.append(f"    // neuron {i}: {code}")
    lines.append("};")
    lines.append("")
    lines.append("parameter [N_OUT*N_HID*2-1:0] W_OUT = {")
    for i, neuron in enumerate(w_out):
        code = ", ".join(f"trit={int(round(w)):+d}" for w in neuron)
        lines.append(f"    // output {i}: {code}")
    lines.append("};")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    torch.manual_seed(0)

    print("Generating training data from pong_hdl.PongLogic ...")
    examples = generate_dataset()
    x, y = to_tensors(examples)
    print(f"{len(examples)} examples")

    model = NeuralNetModel()

    print("\nTraining ...")
    train(model, x, y)

    print("\nTrained weights:")
    print(export_weights(model))
