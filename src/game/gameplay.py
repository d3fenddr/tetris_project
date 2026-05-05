from __future__ import annotations

import queue
import threading
from typing import Callable

import pygame

from src.config import (
    BLACK,
    BLOCK_SIZE,
    COLS,
    FPS,
    GRAY,
    HARD_DROP_SCORE_PER_ROW,
    HUD_MODE_FONT_SIZE,
    HUD_SCORE_FONT_SIZE,
    HUD_SCORE_SHADOW_COLOR,
    HUD_SCORE_SHADOW_OFFSET,
    HUD_SCORE_TEXT_COLOR,
    LOCKED_PIECE_COLOR,
    RED,
    ROWS,
    SHAPES,
    WHITE,
)
from src.game.board import clear_full_rows, create_grid
from src.game.input import KeyRepeatController
from src.game.modes import game_mode_label, piece_weights_for_mode
from src.game.piece import Piece
from src.game.scoring import score_for_cleared_lines
from src.services.score_service import ScoreService
from src.state import AppState
from src.ui.score_effects import ScoreEffectManager
from src.utils.ui_helpers import draw_button, draw_text, draw_text_shadow


def draw_grid(screen: pygame.Surface, background_img: pygame.Surface, grid: list[list[int]]) -> None:
    screen.blit(background_img, (0, 0))
    width, height = screen.get_size()
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x]:
                pygame.draw.rect(
                    screen,
                    LOCKED_PIECE_COLOR,
                    (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                )
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRAY, (0, y * BLOCK_SIZE), (width, y * BLOCK_SIZE), 1)
    for x in range(COLS + 1):
        pygame.draw.line(screen, GRAY, (x * BLOCK_SIZE, 0), (x * BLOCK_SIZE, height), 1)
    pygame.draw.rect(screen, GRAY, (0, 0, width, height), 2)


def _focus_lost(event: pygame.event.Event) -> bool:
    window_focus_lost = getattr(pygame, "WINDOWFOCUSLOST", None)
    if window_focus_lost is not None and event.type == window_focus_lost:
        return True
    return event.type == pygame.ACTIVEEVENT and getattr(event, "gain", 1) == 0


def draw_game_hud(
    screen: pygame.Surface,
    score: int,
    game_mode: str,
    effects: ScoreEffectManager,
    now_ms: int,
) -> None:
    draw_text_shadow(
        screen,
        f"Score: {score}",
        effects.score_font_size(HUD_SCORE_FONT_SIZE, now_ms),
        HUD_SCORE_TEXT_COLOR,
        screen.get_width() // 2,
        27,
        HUD_SCORE_SHADOW_COLOR,
        HUD_SCORE_SHADOW_OFFSET,
    )
    draw_text_shadow(
        screen,
        f"Mode: {game_mode_label(game_mode)}",
        HUD_MODE_FONT_SIZE,
        WHITE,
        screen.get_width() // 2,
        54,
        HUD_SCORE_SHADOW_COLOR,
        HUD_SCORE_SHADOW_OFFSET,
    )


def countdown(screen: pygame.Surface, clock: pygame.time.Clock) -> None:
    for value in range(3, 0, -1):
        screen.fill(BLACK)
        draw_text(screen, str(value), 60, WHITE, screen.get_width() // 2, screen.get_height() // 2)
        pygame.display.update()
        clock.tick(1)


def game_over_screen(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    score: int,
    submit_message: str = "",
    submit_queue: "queue.Queue[str] | None" = None,
) -> bool:
    while True:
        if submit_queue is not None:
            try:
                submit_message = submit_queue.get_nowait()
            except queue.Empty:
                pass
        screen.fill(BLACK)
        draw_text(screen, "GAME OVER", 45, RED, screen.get_width() // 2, screen.get_height() // 3)
        draw_text(screen, f"Score: {score}", 28, WHITE, screen.get_width() // 2, screen.get_height() // 3 + 60)
        if submit_message:
            draw_text(screen, submit_message[:42], 15, GRAY, screen.get_width() // 2, screen.get_height() // 3 + 95)
        play_rect = pygame.Rect(screen.get_width() // 2 - 75, screen.get_height() // 2, 150, 40)
        menu_rect = pygame.Rect(screen.get_width() // 2 - 75, screen.get_height() // 2 + 60, 150, 40)
        mouse_pos = pygame.mouse.get_pos()
        draw_button(screen, play_rect, "Play Again", 22, hovered=play_rect.collidepoint(mouse_pos), selected=True)
        draw_button(screen, menu_rect, "Main Menu", 22, hovered=menu_rect.collidepoint(mouse_pos))
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if play_rect.collidepoint(event.pos):
                    return True
                if menu_rect.collidepoint(event.pos):
                    return False


def main_game(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
    score_service: ScoreService,
    open_pause_menu: Callable[[Callable[[], None], int], str | None],
    on_game_over: Callable[[], None] | None = None,
) -> None:
    while True:
        countdown(screen, clock)

        locked: dict[tuple[int, int], int] = {}
        fall_time = 0
        fall_speed = 1.0
        score = 0
        total_lines = 0
        piece_weights = piece_weights_for_mode(state.game_mode)
        piece = Piece.spawn(SHAPES, piece_weights, COLS)
        effects = ScoreEffectManager()
        key_repeat = KeyRepeatController({})
        single_action_keys_held: set[int] = set()
        running = True

        def current_grid() -> list[list[int]]:
            return create_grid(locked, ROWS, COLS)

        def spawn_piece() -> Piece:
            return Piece.spawn(SHAPES, piece_weights, COLS)

        def move_piece(dx: int, dy: int) -> bool:
            nonlocal piece
            grid = current_grid()
            if piece.valid_move(dx, dy, grid, COLS, ROWS):
                piece.x += dx
                piece.y += dy
                return True
            return False

        def lock_piece(now_ms: int) -> None:
            nonlocal locked, piece, running, score, total_lines, fall_time
            for x, y in piece.get_cells():
                locked[(x, y)] = 1

            locked, cleared = clear_full_rows(locked, ROWS, COLS)
            if cleared:
                total_lines += cleared
                points = score_for_cleared_lines(cleared)
                score += points
                effects.add_line_clear(
                    points=points,
                    lines=cleared,
                    now_ms=now_ms,
                    x=screen.get_width() // 2,
                    y=screen.get_height() // 2,
                )

            piece = spawn_piece()
            grid = current_grid()
            if not piece.valid_move(0, 0, grid, COLS, ROWS):
                running = False
                key_repeat.clear()
                single_action_keys_held.clear()
            fall_time = 0

        def soft_drop() -> None:
            nonlocal fall_time
            now_ms = pygame.time.get_ticks()
            if not move_piece(0, 1):
                lock_piece(now_ms)
            fall_time = 0

        def hard_drop() -> None:
            nonlocal score
            now_ms = pygame.time.get_ticks()
            dropped_rows = 0
            while move_piece(0, 1):
                dropped_rows += 1
            if dropped_rows and HARD_DROP_SCORE_PER_ROW > 0:
                points = dropped_rows * HARD_DROP_SCORE_PER_ROW
                score += points
                effects.add_score(
                    points=points,
                    now_ms=now_ms,
                    x=screen.get_width() // 2,
                    y=96,
                )
            lock_piece(now_ms)

        key_repeat.actions = {
            pygame.K_LEFT: lambda: move_piece(-1, 0),
            pygame.K_RIGHT: lambda: move_piece(1, 0),
            pygame.K_DOWN: soft_drop,
        }

        def draw_frame() -> None:
            now_ms = pygame.time.get_ticks()
            grid = current_grid()
            draw_grid(screen, background_img, grid)
            piece.draw(screen, BLOCK_SIZE, WHITE, BLACK)
            effects.draw_board_flash(
                screen,
                pygame.Rect(0, 0, screen.get_width(), screen.get_height()),
                now_ms,
            )
            draw_game_hud(screen, score, state.game_mode, effects, now_ms)
            effects.draw_popups(screen, now_ms)

        while running:
            dt = clock.tick(FPS)
            now_ms = pygame.time.get_ticks()
            fall_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if _focus_lost(event):
                    key_repeat.clear()
                    single_action_keys_held.clear()
                if event.type == pygame.KEYUP:
                    key_repeat.release(event.key)
                    single_action_keys_held.discard(event.key)
                if event.type == pygame.KEYDOWN:
                    if key_repeat.press(event.key, now_ms):
                        continue
                    elif event.key == pygame.K_UP:
                        if event.key in single_action_keys_held:
                            continue
                        single_action_keys_held.add(event.key)
                        piece.rotate(current_grid(), COLS, ROWS)
                    elif event.key == pygame.K_SPACE:
                        if event.key in single_action_keys_held:
                            continue
                        single_action_keys_held.add(event.key)
                        hard_drop()
                    elif event.key == pygame.K_ESCAPE:
                        key_repeat.clear()
                        single_action_keys_held.clear()
                        result = open_pause_menu(draw_frame, score)
                        key_repeat.clear()
                        single_action_keys_held.clear()
                        if result == "exit":
                            return

            if running:
                key_repeat.update(now_ms)

            if running and fall_time / 1000 >= fall_speed:
                if not move_piece(0, 1):
                    lock_piece(now_ms)
                fall_time = 0

            draw_frame()
            pygame.display.update()

        key_repeat.clear()
        single_action_keys_held.clear()
        if on_game_over is not None:
            on_game_over()
        submit_queue: "queue.Queue[str]" = queue.Queue()

        def submit_worker() -> None:
            submitted = score_service.record_score(
                state.player_name,
                score,
                mode=state.game_mode,
                lines=total_lines,
                level=1,
            )
            message = "Season 2 score submitted." if submitted else "Score not submitted. Check backend."
            submit_queue.put(message)

        threading.Thread(target=submit_worker, daemon=True).start()
        if not game_over_screen(screen, clock, score, "Submitting Season 2 score...", submit_queue):
            break
