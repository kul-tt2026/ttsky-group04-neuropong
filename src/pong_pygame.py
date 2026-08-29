"""
Pygame frontend for pong_hdl_exact.py.

The game physics are NOT reimplemented here.
PongLogic remains the single source of truth.

Keyboard:
    W / S       = left paddle up / down
    UP / DOWN    = right paddle up / down
    ESC          = quit

Pygame is only a visualization/input layer.

Timing:
    - The Python model is advanced by one clk edge per tick of
      PongLogic.clock().
    - frame_tick is generated at the same game-update cadence as the HDL
      expects. It is deliberately kept separate from the Pygame rendering
      loop.
    - Rendering does not modify the game state.
"""

import sys
import pygame

from pong_hdl import PongLogic


# ---------------------------------------------------------------------------
# Display constants: these mirror the HDL display coordinates.
# ---------------------------------------------------------------------------

WIDTH = PongLogic.H_DISPLAY #640
HEIGHT = PongLogic.V_DISPLAY #480
X = PongLogic.X # 15

PADDLE_WIDTH = X
PADDLE_HEIGHT = PongLogic.PADDLE_HEIGHT

L_PADDLE_X = PongLogic.L_PADDLE_X
R_PADDLE_X = PongLogic.R_PADDLE_X

# VGA/game update cadence.
# The HDL receives clk and frame_tick separately. Pygame needs a practical
# clock for simulation, so this is the rate at which we assert frame_tick.
GAME_FPS = 60

# Rendering can run faster than the game if desired.
RENDER_FPS = 60


def draw_game(screen, game: PongLogic):
    """
    Draw ONLY the state of PongLogic.

    No physics or collision logic is performed here.
    """

    screen.fill((0, 0, 0))

    # Ball
    pygame.draw.rect(
        screen,
        (255, 255, 255),
        pygame.Rect(
            game.ball_x,
            game.ball_y,
            X,
            X,
        ),
    )

    # Left paddle
    pygame.draw.rect(
        screen,
        (255, 0, 0),
        pygame.Rect(
            L_PADDLE_X,
            game.l_paddle_y,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        ),
    )

    # Right paddle
    pygame.draw.rect(
        screen,
        (0, 0, 255),
        pygame.Rect(
            R_PADDLE_X,
            game.r_paddle_y,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        ),
    )

    # Center line is visualization only.
    # It has no influence whatsoever on PongLogic.
    for y in range(0, HEIGHT, 12):
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            pygame.Rect(WIDTH // 2 - 1, y, 2, 6),
        )

    # Scores
    font = pygame.font.Font(None, 48)

    left_score = font.render(
        str(game.l_score),
        True,
        (255, 255, 255),
    )

    right_score = font.render(
        str(game.r_score),
        True,
        (255, 255, 255),
    )

    screen.blit(left_score, (WIDTH // 2 - 70, 20))
    screen.blit(right_score, (WIDTH // 2 + 50, 20))

    if game.game_over:
        game_over_font = pygame.font.Font(None, 64)
        text = game_over_font.render(
            "GAME OVER",
            True,
            (255, 255, 255),
        )

        screen.blit(
            text,
            (
                WIDTH // 2 - text.get_width() // 2,
                HEIGHT // 2 - text.get_height() // 2,
            ),
        )

    pygame.display.flip()


def main():
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tiny Tapeout Pong - HDL exact simulation")

    render_clock = pygame.time.Clock()

    game = PongLogic()

    running = True

    # Accumulator lets rendering run independently from the HDL game-update
    # cadence. The game state itself is changed only by game.clock().
    accumulator = 0.0
    game_period = 1.0 / GAME_FPS

    previous_time = pygame.time.get_ticks() / 1000.0

    while running:
        current_time = pygame.time.get_ticks() / 1000.0
        elapsed = current_time - previous_time
        previous_time = current_time

        # Avoid a huge catch-up after pausing/debugging.
        elapsed = min(elapsed, 0.25)
        accumulator += elapsed

        # ---------------------------------------------------------------
        # Inputs are sampled just before each frame_tick.
        # ---------------------------------------------------------------

        keys = pygame.key.get_pressed()

        l_paddle_up = bool(keys[pygame.K_z])
        l_paddle_down = bool(keys[pygame.K_s])

        r_paddle_up = bool(keys[pygame.K_UP])
        r_paddle_down = bool(keys[pygame.K_DOWN])

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # ---------------------------------------------------------------
        # Advance the exact HDL model.
        # ---------------------------------------------------------------
        #
        # Every time one game period has elapsed, this corresponds to the
        # frame_tick pulse used by pong_logic.v.
        #
        # Pygame rendering itself NEVER advances the game.
        #

        while accumulator >= game_period:
            accumulator -= game_period

            game.clock(
                reset_n=True,
                game_reset=False,
                frame_tick=True,
                l_paddle_up=l_paddle_up,
                l_paddle_down=l_paddle_down,
                r_paddle_up=r_paddle_up,
                r_paddle_down=r_paddle_down,
            )

        # ---------------------------------------------------------------
        # Rendering only.
        # ---------------------------------------------------------------

        draw_game(screen, game)

        render_clock.tick(RENDER_FPS)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
