"""
Python bit-accurate model of the current Tiny Tapeout Pong HDL.

Source HDL replicated:
    - pong_logic.v
    - paddle_reflection.v

IMPORTANT:
This is intentionally written to preserve HDL behavior rather than to make
the Python implementation "nicer". In particular:
    * 10-bit/7-bit/8-bit/4-bit wrapping is emulated.
    * signed 10-bit ball velocities are emulated.
    * non-blocking-assignment behavior is emulated by calculating all next
      state from the OLD state and committing it at the end of the clock.
    * the collision pipeline is preserved.
    * paddle_reflection is combinational, just like always @(*).
    * frame_phase is used with its OLD value in the same clock, matching
      non-blocking Verilog semantics.
    * frame_tick only advances game state when it is true.
    * the paddle inputs are l_paddle_up/down and r_paddle_up/down

The intended training loop is therefore:

    state = game.observe()
    nn_output = neural_network(state)
    game.step(frame_tick=True,
              l_paddle_up=...,
              l_paddle_down=...,
              r_paddle_up=...,
              r_paddle_down=...)

The values returned by observe() correspond to the HDL output signals.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


# ---------------------------------------------------------------------------
# Verilog-style integer helpers
# ---------------------------------------------------------------------------

def u(value: int, bits: int) -> int:
    """Convert int to unsigned bits"""
    return value & ((1 << bits) - 1)


def s(value: int, bits: int) -> int:
    """Interpret a fixed-width bit pattern as a signed Verilog value."""
    value &= (1 << bits) - 1
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value


def bit(value: int, index: int) -> int:
    """Look at bit on index"""
    return (value >> index) & 1


def max10(a: int, b: int) -> int:
    return a if a >= b else b


def min10(a: int, b: int) -> int:
    return a if a <= b else b


# ---------------------------------------------------------------------------
# paddle_reflection.v
# ---------------------------------------------------------------------------

class PaddleReflection:
    """
    Inputs:
        ball_y
        paddle_y
        l_paddle_collision
        r_paddle_collision

    Outputs:
        reflection_vx
        reflection_vy

    The HDL calculates:
        diff = ball_y - paddle_y + X;
        relative_position = diff[6:0];
    """

    X = 15

    @staticmethod       #class variables
    def calculate(
        # IO
        ball_y: int,
        paddle_y: int,
        l_paddle_collision: bool,
        r_paddle_collision: bool,
    ) -> Tuple[int, int]:           #signed reflection_vx, signed reflection_vy

        """ always @(*) begin """

        # reg [9:0] diff;
        diff = u(ball_y - paddle_y + PaddleReflection.X, 10)

        # reg [6:0] relative_position;
        relative_position = u(diff, 7)

        # reg signed [9:0] vx_abs;
        vx_abs = 0
        reflection_vx = 0
        reflection_vy = 0



        # Exact table from the HDL.
        if relative_position <= 8:
            vx_abs = 5
            reflection_vy = -5

        elif 9 <= relative_position <= 19:
            vx_abs = 6
            reflection_vy = -4

        elif 20 <= relative_position <= 31:
            vx_abs = 6
            reflection_vy = -3

        elif 32 <= relative_position <= 42:
            vx_abs = 7
            reflection_vy = -2

        elif 43 <= relative_position <= 47:
            vx_abs = 7
            reflection_vy = 0

        elif 48 <= relative_position <= 58:
            vx_abs = 7
            reflection_vy = 2

        elif 59 <= relative_position <= 70:
            vx_abs = 6
            reflection_vy = 3

        elif 71 <= relative_position <= 81:
            vx_abs = 6
            reflection_vy = 4

        elif relative_position >= 82:
            vx_abs = 5
            reflection_vy = 5

        if l_paddle_collision:
            reflection_vx = vx_abs

        elif r_paddle_collision:
            reflection_vx = -vx_abs

        # reflection_vx/reflection_vy are signed [9:0] in the HDL.
        return s(reflection_vx, 10), s(reflection_vy, 10)


# ---------------------------------------------------------------------------
# Pong state
# ---------------------------------------------------------------------------

@dataclass
class PongOutputs:
    l_paddle_y: int
    r_paddle_y: int
    ball_x: int
    ball_y: int
    ball_dir_x: int
    ball_dir_y: int
    l_score: int
    r_score: int
    winner: int
    game_over: int


class PongLogic:
    """
    One call to clock() represents ONE posedge clk.

    Do not call clock() once per video frame unless your HDL frame_tick is
    also asserted once per video frame. The HDL itself receives both clk and
    frame_tick, so this class preserves that separation.
    """

    V_DISPLAY = 480
    H_DISPLAY = 640

    X = 15
    L_PADDLE_X = 2 * X
    R_PADDLE_X = H_DISPLAY - 3 * X
    PADDLE_HEIGHT = 5 * X

    PADDLE_SPEED = 5
    GAME_OVER_FRAMES = 180

    def __init__(self):
        # the reg declarations in pong_logic.v.
        self.l_paddle_y = 0
        self.r_paddle_y = 0

        self.ball_x = 0
        self.ball_y = 0

        self.l_score = 0
        self.r_score = 0

        self.winner = 0
        self.game_over = 0

        self.pause_counter = 0
        self.frame_phase = 0

        self.l_paddle_hit = 0
        self.r_paddle_hit = 0
        self.l_front_hit = 0
        self.r_front_hit = 0

        # signed [9:0]
        self.ball_vx = 0
        self.ball_vy = 0

        # Same as power-on reset through reset_n=0.
        self.clock(reset_n=False, game_reset=False, frame_tick=False)

    # -----------------------------------------------------------------------
    # Combinational signals from pong_logic.v
    # -----------------------------------------------------------------------

    def _abs_ball_vx(self) -> int:
        # wire [9:0] abs_ball_vx = ball_vx[9] ? -ball_vx : ball_vx;
        return u(-self.ball_vx if s(self.ball_vx, 10) < 0 else self.ball_vx, 10)

    def _abs_ball_vy(self) -> int:
        # wire [9:0] abs_ball_vy = ball_vy[9] ? -ball_vy : ball_vy;
        return u(-self.ball_vy if s(self.ball_vy, 10) < 0 else self.ball_vy, 10)

    def _ball_vx_signed(self) -> int:
        return s(self.ball_vx, 10)

    def _ball_vy_signed(self) -> int:
        return s(self.ball_vy, 10)

    def _combinational(self) -> Dict[str, int]:
        """
        Reproduce the wires in pong_logic.v using the current (pre-clock)
        state.
        """

        ball_vx = self._ball_vx_signed()
        ball_vy = self._ball_vy_signed()
        abs_ball_vx = self._abs_ball_vx()
        abs_ball_vy = self._abs_ball_vy()

        # wire top_hit = (ball_y <= abs_ball_vy && ball_vy < 0);
        top_hit = int(self.ball_y <= abs_ball_vy and ball_vy < 0)

        # wire bottom_hit = (ball_y + X + abs_ball_vy >= V_DISPLAY && ball_vy > 0);
        bottom_hit = int(u(self.ball_y + self.X + abs_ball_vy, 10) >= self.V_DISPLAY and ball_vy > 0)

        # wire [9:0] pred_x = ball_x + ball_vx;
        pred_x = u(self.ball_x + ball_vx, 10)

        # wire [9:0] pred_y = ball_y + ball_vy;
        pred_y = u(self.ball_y + ball_vy, 10)

        # l_x_overlap = (pred_x + X < L_PADDLE_X + X ? pred_x + X : L_PADDLE_X + X) - (pred_x > L_PADDLE_X ? pred_x : L_PADDLE_X);
        l_x_overlap = u(min10(u(pred_x + self.X, 10),
                  u(self.L_PADDLE_X + self.X, 10))
            - max10(pred_x, self.L_PADDLE_X), 10)

        # l_y_overlap = (pred_y + X < l_paddle_y + PADDLE_HEIGHT ? pred_y + X : l_paddle_y + PADDLE_HEIGHT) - (pred_y > l_paddle_y ? pred_y : l_paddle_y);
        l_y_overlap = u(min10(u(pred_y + self.X, 10),
                  u(self.l_paddle_y + self.PADDLE_HEIGHT, 10))
            - max10(pred_y, self.l_paddle_y), 10)

        # r_x_overlap = (pred_x + X < R_PADDLE_X + X ? pred_x + X : R_PADDLE_X + X) - (pred_x > R_PADDLE_X ? pred_x : R_PADDLE_X);
        r_x_overlap = u(
            min10(u(pred_x + self.X, 10),
                  u(self.R_PADDLE_X + self.X, 10))
            - max10(pred_x, self.R_PADDLE_X),
            10
        )

        # r_y_overlap = (pred_y + X < r_paddle_y + PADDLE_HEIGHT ? pred_y + X : r_paddle_y + PADDLE_HEIGHT) - (pred_y > r_paddle_y ? pred_y : r_paddle_y);
        r_y_overlap = u(min10(u(pred_y + self.X, 10),
                  u(self.r_paddle_y + self.PADDLE_HEIGHT, 10))
            - max10(pred_y, self.r_paddle_y),10)

        # assign ball_dir_x = ball_vx[9];
        ball_dir_x = bit(self.ball_vx, 9)

        # assign ball_dir_y = ball_vy[9];
        ball_dir_y = bit(self.ball_vy, 9)

        # wire selected_paddle_y = l_paddle_hit ? l_paddle_y : r_paddle_y;
        selected_paddle_y = (self.l_paddle_y if self.l_paddle_hit
            else self.r_paddle_y
        )

        # paddle_reflection is combinational.
        reflection_vx, reflection_vy = PaddleReflection.calculate(
            self.ball_y,
            selected_paddle_y,
            bool(self.l_paddle_hit),
            bool(self.r_paddle_hit),
        )

        return {
            "top_hit": top_hit,
            "bottom_hit": bottom_hit,
            "pred_x": pred_x,
            "pred_y": pred_y,
            "l_x_overlap": l_x_overlap,
            "l_y_overlap": l_y_overlap,
            "r_x_overlap": r_x_overlap,
            "r_y_overlap": r_y_overlap,
            "ball_dir_x": ball_dir_x,
            "ball_dir_y": ball_dir_y,
            "abs_ball_vx": abs_ball_vx,
            "abs_ball_vy": abs_ball_vy,
            "reflection_vx": reflection_vx,
            "reflection_vy": reflection_vy,
        }

    # -----------------------------------------------------------------------
    # Outputs / state observation
    # -----------------------------------------------------------------------

    def outputs(self) -> PongOutputs:
        c = self._combinational()

        return PongOutputs(
            l_paddle_y=self.l_paddle_y,
            r_paddle_y=self.r_paddle_y,
            ball_x=self.ball_x,
            ball_y=self.ball_y,
            ball_dir_x=c["ball_dir_x"],
            ball_dir_y=c["ball_dir_y"],
            l_score=self.l_score,
            r_score=self.r_score,
            winner=self.winner,
            game_over=self.game_over,
        )

    def observe(self) -> Dict[str, int]:  #inputs for neural network training
        """
        Convenient dictionary for a Python neural-network training loop.
        These are the same externally visible game signals that the HDL
        exposes to the neural_net module.
        """
        o = self.outputs()
        return {
            "ball_y": o.ball_y,
            "ball_dir_x": o.ball_dir_x,
            "ball_dir_y": o.ball_dir_y,
            "l_paddle_y": o.l_paddle_y,
            "r_paddle_y": o.r_paddle_y,
            "l_score": o.l_score,
            "r_score": o.r_score,
            "winner": o.winner,
            "game_over": o.game_over,
        }

    # -----------------------------------------------------------------------
    # One posedge clk
    # -----------------------------------------------------------------------

    def clock(
        self,
        reset_n: bool = True,
        game_reset: bool = False,
        frame_tick: bool = False,
        l_paddle_up: bool = False,
        l_paddle_down: bool = False,
        r_paddle_up: bool = False,
        r_paddle_down: bool = False,
    ) -> PongOutputs:
        """
        Simulate exactly one:

            always @(posedge clk)

        event.

        All inputs are sampled at this clock edge.

        Non-blocking assignments are modeled by keeping old state throughout
        the calculations and committing next-state only after all logic has
        been evaluated.
        """

        # ================================================================
        # First always @(posedge clk):
        # collision pipeline
        # ================================================================

        # These are the values of the combinational wires BEFORE this
        # clock edge, exactly like the HDL.
        c = self._combinational()

        next_l_paddle_hit = self.l_paddle_hit
        next_r_paddle_hit = self.r_paddle_hit
        next_l_front_hit = self.l_front_hit
        next_r_front_hit = self.r_front_hit

        if (not reset_n) or game_reset:
            next_l_paddle_hit = 0
            next_r_paddle_hit = 0
            next_l_front_hit = 0
            next_r_front_hit = 0

        else:
            # l_paddle_hit <= ...
            old_ball_vx = self._ball_vx_signed()

            next_l_paddle_hit = int(old_ball_vx < 0 and
                (self.ball_x <=
                    self.L_PADDLE_X + self.X + c["abs_ball_vx"]
                    and
                    self.ball_x + self.X >= self.L_PADDLE_X)
                and
                (self.ball_y + self.X >= self.l_paddle_y
                    and
                    self.ball_y <
                    self.l_paddle_y + self.PADDLE_HEIGHT))

            # r_paddle_hit <= ...
            next_r_paddle_hit = int(old_ball_vx > 0 and
                (self.ball_x <= self.R_PADDLE_X + self.X
                    and
                    self.ball_x + self.X + c["abs_ball_vx"] >=
                    self.R_PADDLE_X)
                and
                (self.ball_y + self.X >= self.r_paddle_y
                    and
                    self.ball_y <
                    self.r_paddle_y + self.PADDLE_HEIGHT))

            # l_front_hit <= (l_x_overlap <= l_y_overlap);
            next_l_front_hit = int(c["l_x_overlap"] <= c["l_y_overlap"])

            # r_front_hit <= (r_x_overlap <= r_y_overlap);
            next_r_front_hit = int(c["r_x_overlap"] <= c["r_y_overlap"])

        # ================================================================
        # Second always @(posedge clk):
        # pong/game state
        # ================================================================

        # Start with exact old state, as would happen if no assignment
        # reaches a particular register in this clock.
        next_l_paddle_y = self.l_paddle_y
        next_r_paddle_y = self.r_paddle_y
        next_ball_x = self.ball_x
        next_ball_y = self.ball_y

        next_ball_vx = self._ball_vx_signed()
        next_ball_vy = self._ball_vy_signed()

        next_pause_counter = self.pause_counter
        next_game_over = self.game_over
        next_winner = self.winner
        next_frame_phase = self.frame_phase
        next_l_score = self.l_score
        next_r_score = self.r_score

        if (not reset_n) or game_reset:
            # l_paddle_y <= V_DISPLAY/2 - 3*X/2;
            next_l_paddle_y = self.V_DISPLAY // 2 - (3 * self.X) // 2
            next_r_paddle_y = self.V_DISPLAY // 2 - (3 * self.X) // 2

            # ball_x <= H_DISPLAY/2 - X/2;
            next_ball_x = self.H_DISPLAY // 2 - self.X // 2
            next_ball_y = self.V_DISPLAY // 2 - self.X // 2

            next_ball_vx = -3
            next_ball_vy = 2

            next_pause_counter = 0
            next_game_over = 0
            next_winner = 0
            next_frame_phase = 0

            next_l_score = 0
            next_r_score = 0

        elif frame_tick:

            if self.game_over:

                if self.pause_counter == self.GAME_OVER_FRAMES:
                    next_l_paddle_y = (self.V_DISPLAY // 2 - (3 * self.X) // 2)
                    next_r_paddle_y = (self.V_DISPLAY // 2 - (3 * self.X) // 2)

                    next_ball_x = self.H_DISPLAY // 2 - self.X // 2
                    next_ball_y = self.V_DISPLAY // 2 - self.X // 2

                    if self.frame_phase:
                        next_ball_vx = 3
                    else:
                        next_ball_vx = -3

                    next_ball_vy = 2

                    next_l_score = 0
                    next_r_score = 0
                    next_game_over = 0
                    next_pause_counter = 0
                    next_winner = 0

                else:
                    # pause_counter <= pause_counter + 1;
                    next_pause_counter = u(self.pause_counter + 1, 8)

            else:
                # frame_phase <= ~frame_phase;
                next_frame_phase = int(not self.frame_phase)

                # ========================================================
                # Y-axis LOGIC
                # ========================================================

                if c["top_hit"]:
                    # ball_vy <= -ball_vy;
                    next_ball_vy = -self._ball_vy_signed()

                    # ball_y <= abs_ball_vy - ball_y;
                    next_ball_y = u(c["abs_ball_vy"] - self.ball_y, 10)

                elif c["bottom_hit"]:
                    # ball_vy <= -ball_vy;
                    next_ball_vy = -self._ball_vy_signed()

                    # ball_y <= (V_DISPLAY - X) -
                    #           ((ball_y + X + abs_ball_vy) - V_DISPLAY);
                    next_ball_y = u(
                        (self.V_DISPLAY - self.X)
                        - (
                            (self.ball_y + self.X + c["abs_ball_vy"])
                            - self.V_DISPLAY
                        ),
                        10
                    )

                else:
                    # ball_y <= ball_y + ball_vy;
                    next_ball_y = u(
                        self.ball_y + self._ball_vy_signed(), 10
                    )

                # ========================================================
                # X-axis LOGIC
                # ========================================================

                if self.ball_x <= c["abs_ball_vx"]:
                    # ball_vx <= 10'sd3;
                    next_ball_vx = 3

                    # IMPORTANT: old frame_phase.
                    if self.frame_phase:
                        next_ball_vy = 1
                    else:
                        next_ball_vy = -1

                    next_ball_x = self.H_DISPLAY // 2 - self.X // 2
                    next_ball_y = self.V_DISPLAY // 2 - self.X // 2

                    if self.r_score == 9:
                        next_winner = 1
                        next_game_over = 1
                    else:
                        next_r_score = u(self.r_score + 1, 4)

                elif (
                    self.ball_x + self.X + c["abs_ball_vx"]
                    >= self.H_DISPLAY
                ):
                    # ball_vx <= -3;
                    next_ball_vx = -3

                    # IMPORTANT: old frame_phase.
                    if self.frame_phase:
                        next_ball_vy = 1
                    else:
                        next_ball_vy = -1

                    next_ball_x = self.H_DISPLAY // 2 - self.X // 2
                    next_ball_y = self.V_DISPLAY // 2 - self.X // 2

                    if self.l_score == 9:
                        next_winner = 0
                        next_game_over = 1
                    else:
                        next_l_score = u(self.l_score + 1, 4)

                elif self.l_paddle_hit:
                    # reflection_vx/reflection_vy are based on the OLD
                    # collision pipeline values, exactly as in the HDL.
                    selected_paddle_y = (
                        self.l_paddle_y
                        if self.l_paddle_hit
                        else self.r_paddle_y
                    )

                    reflection_vx, reflection_vy = (
                        PaddleReflection.calculate(
                            self.ball_y,
                            selected_paddle_y,
                            bool(self.l_paddle_hit),
                            bool(self.r_paddle_hit),
                        )
                    )

                    next_ball_vx = reflection_vx
                    next_ball_vy = reflection_vy

                    if self.l_front_hit:
                        next_ball_x = self.L_PADDLE_X + self.X
                    elif c["pred_y"] < self.l_paddle_y:
                        next_ball_y = self.l_paddle_y - self.X
                    else:
                        next_ball_y = (
                            self.l_paddle_y + self.PADDLE_HEIGHT
                        )

                elif self.r_paddle_hit:
                    selected_paddle_y = self.r_paddle_y

                    reflection_vx, reflection_vy = (
                        PaddleReflection.calculate(
                            self.ball_y,
                            selected_paddle_y,
                            bool(self.l_paddle_hit),
                            bool(self.r_paddle_hit),
                        ))

                    next_ball_vx = reflection_vx
                    next_ball_vy = reflection_vy

                    if self.r_front_hit:
                        next_ball_x = self.R_PADDLE_X - self.X
                    elif c["pred_y"] < self.r_paddle_y:
                        next_ball_y = self.r_paddle_y - self.X
                    else:
                        next_ball_y = (self.r_paddle_y + self.PADDLE_HEIGHT)

                elif c["ball_dir_x"] == 0:
                    # ball_x <= ball_x + abs_ball_vx;
                    next_ball_x = u(self.ball_x + c["abs_ball_vx"], 10)

                else:
                    # ball_x <= ball_x - abs_ball_vx;
                    next_ball_x = u(self.ball_x - c["abs_ball_vx"], 10)

                # ========================================================
                # Paddle movement LOGIC
                # ========================================================

                # Left paddle
                if l_paddle_down and not l_paddle_up:
                    if (self.l_paddle_y
                        + self.PADDLE_HEIGHT
                        + self.PADDLE_SPEED
                        <= self.V_DISPLAY):

                        next_l_paddle_y = u(self.l_paddle_y + self.PADDLE_SPEED, 10)
                    else:
                        next_l_paddle_y = (self.V_DISPLAY - self.PADDLE_HEIGHT)

                elif not l_paddle_down and l_paddle_up:
                    if self.l_paddle_y >= self.PADDLE_SPEED:
                        next_l_paddle_y = u(self.l_paddle_y - self.PADDLE_SPEED, 10)
                    else:
                        next_l_paddle_y = 0

                # Right paddle
                if r_paddle_down and not r_paddle_up:
                    if (self.r_paddle_y
                        + self.PADDLE_HEIGHT
                        + self.PADDLE_SPEED
                        <= self.V_DISPLAY):

                        next_r_paddle_y = u(self.r_paddle_y + self.PADDLE_SPEED, 10)
                    else:
                        next_r_paddle_y = (self.V_DISPLAY - self.PADDLE_HEIGHT)

                elif not r_paddle_down and r_paddle_up:
                    if self.r_paddle_y >= self.PADDLE_SPEED:
                        next_r_paddle_y = u(self.r_paddle_y - self.PADDLE_SPEED, 10)
                    else:
                        next_r_paddle_y = 0

        # ================================================================
        # Commit all non-blocking assignments simultaneously.
        # ================================================================

        self.l_paddle_y = u(next_l_paddle_y, 10)
        self.r_paddle_y = u(next_r_paddle_y, 10)

        self.ball_x = u(next_ball_x, 10)
        self.ball_y = u(next_ball_y, 10)

        self.ball_vx = u(next_ball_vx, 10)
        self.ball_vy = u(next_ball_vy, 10)

        self.l_score = u(next_l_score, 4)
        self.r_score = u(next_r_score, 4)

        self.winner = int(bool(next_winner))
        self.game_over = int(bool(next_game_over))

        self.pause_counter = u(next_pause_counter, 8)
        self.frame_phase = int(bool(next_frame_phase))

        self.l_paddle_hit = int(bool(next_l_paddle_hit))
        self.r_paddle_hit = int(bool(next_r_paddle_hit))
        self.l_front_hit = int(bool(next_l_front_hit))
        self.r_front_hit = int(bool(next_r_front_hit))

        return self.outputs()


# ---------------------------------------------------------------------------
# Training-oriented helper
# ---------------------------------------------------------------------------

def make_training_input(game: PongLogic, paddle: str = "right") -> Tuple[int, int, int]:
    """
    Return exactly the three input features currently used by neural_net.v:

        t_diff
        t_dir_y
        t_dir_x

    This function does NOT implement the neural network. It only creates the
    same ternary game-state inputs so a Python NN can be trained against the
    exact HDL game.

    neural_net.v currently uses:
        diff = ball_y - paddle_y
        DEAD_ZONE = 30
        t_diff = +1 if diff > 30
                  -1 if diff < -30
                   0 otherwise

        t_dir_y = +1 when ball_dir_y == 1, else -1
        t_dir_x = +1 when ball_dir_x == 1, else -1
    """

    if paddle == "left":
        paddle_y = game.l_paddle_y
    elif paddle == "right":
        paddle_y = game.r_paddle_y
    else:
        raise ValueError("paddle must be 'left' or 'right'")

    diff = s(
        u(game.ball_y, 10) - u(paddle_y, 10),
        11,
    )

    if diff > 30:
        t_diff = 1
    elif diff < -30:
        t_diff = -1
    else:
        t_diff = 0

    c = game._combinational()
    t_dir_y = 1 if c["ball_dir_y"] else -1
    t_dir_x = 1 if c["ball_dir_x"] else -1

    return t_diff, t_dir_y, t_dir_x


# ---------------------------------------------------------------------------
# Simple self-tests
# ---------------------------------------------------------------------------

def self_test() -> None:
    """Basic checks for the bit-accurate model."""

    # Reset state must match pong_logic.v.
    game = PongLogic()
    o = game.outputs()

    assert o.l_paddle_y == 218
    assert o.r_paddle_y == 218
    assert o.ball_x == 313
    assert o.ball_y == 233
    assert game.ball_vx == u(-3, 10)
    assert game.ball_vy == 2
    assert o.ball_dir_x == 1
    assert o.ball_dir_y == 0
    assert o.l_score == 0
    assert o.r_score == 0
    assert o.game_over == 0

    # Exact paddle-reflection table.
    expected = [
        (8, 5, -5),
        (9, 6, -4),
        (19, 6, -4),
        (20, 6, -3),
        (31, 6, -3),
        (32, 7, -2),
        (42, 7, -2),
        (43, 7, 0),
        (47, 7, 0),
        (48, 7, 2),
        (58, 7, 2),
        (59, 6, 3),
        (70, 6, 3),
        (71, 6, 4),
        (81, 6, 4),
        (82, 5, 5),
        (89, 5, 5),
    ]

    # Choose paddle_y=100 and construct ball_y such that:
    # ball_y - paddle_y + 15 == relative_position.
    for relative_position, vx, vy in expected:
        ball_y = 100 + relative_position - 15
        got_vx, got_vy = PaddleReflection.calculate(
            ball_y, 100, True, False
        )
        assert (got_vx, got_vy) == (vx, vy), (
            relative_position, got_vx, got_vy, vx, vy
        )

    # Right-paddle direction must be negative.
    vx, vy = PaddleReflection.calculate(150, 100, False, True)
    # 150 - 100 + 15 = 65, which is the 59..70 table entry.
    assert vx == -6
    assert vy == 3

    print("All bit-accuracy self-tests passed.")


if __name__ == "__main__":
    self_test()

    # Example:
    game = PongLogic()

    print("Initial HDL-equivalent state:")
    print(game.outputs())

    # One game update (only because frame_tick=True).
    game.clock(
        frame_tick=True,
        r_paddle_up=True,
    )

    print("\nAfter one frame_tick:")
    print(game.outputs())
