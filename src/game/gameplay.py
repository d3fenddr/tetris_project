from __future__ import annotations

import queue
import threading
from typing import Callable

import pygame

from src.config import (
    BLACK,
    COLS,
    FALL_SPEED_BASE_SECONDS,
    FALL_SPEED_DECREASE_PER_LEVEL,
    FALL_SPEED_MIN_SECONDS,
    FALL_SPEED_SCORE_STEP,
    FPS,
    GAME_OVER_REVEAL_DELAY_MS,
    GRAY,
    HARD_DROP_SCORE_PER_ROW,
    HUD_MODE_FONT_SIZE,
    HUD_SCORE_FONT_SIZE,
    HUD_SCORE_SHADOW_COLOR,
    HUD_SCORE_SHADOW_OFFSET,
    HUD_SCORE_TEXT_COLOR,
    LOCKED_PIECE_COLOR,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
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
from src.utils.layout import calculate_layout, handle_resize_event
from src.utils.ui_helpers import draw_button, draw_image_cover, draw_panel, draw_text, draw_text_shadow


def get_level(score: int) -> int:
    return max(1, score // FALL_SPEED_SCORE_STEP + 1)


def get_fall_speed(score: int) -> float:
    return max(
        FALL_SPEED_MIN_SECONDS,
        FALL_SPEED_BASE_SECONDS - (get_level(score) - 1) * FALL_SPEED_DECREASE_PER_LEVEL,
    )


def draw_grid(screen: pygame.Surface, background_img: pygame.Surface, grid: list[list[int]]) -> None:
    layout = calculate_layout(screen.get_width(), screen.get_height())
    draw_image_cover(screen, background_img)
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x]:
                pygame.draw.rect(
                    screen,
                    LOCKED_PIECE_COLOR,
                    (
                        layout.board_x + x * layout.block_size,
                        layout.board_y + y * layout.block_size,
                        layout.block_size,
                        layout.block_size,
                    ),
                )
    for y in range(ROWS + 1):
        py = layout.board_y + y * layout.block_size
        pygame.draw.line(screen, GRAY, (layout.board_x, py), (layout.board_x + layout.board_width, py), 1)
    for x in range(COLS + 1):
        px = layout.board_x + x * layout.block_size
        pygame.draw.line(screen, GRAY, (px, layout.board_y), (px, layout.board_y + layout.board_height), 1)
    pygame.draw.rect(screen, GRAY, (layout.board_x, layout.board_y, layout.board_width, layout.board_height), 2)


def _focus_lost(event: pygame.event.Event) -> bool:
    window_focus_lost = getattr(pygame, "WINDOWFOCUSLOST", None)
    if window_focus_lost is not None and event.type == window_focus_lost:
        return True
    return event.type == pygame.ACTIVEEVENT and getattr(event, "gain", 1) == 0


def draw_game_hud(
    screen: pygame.Surface,
    score: int,
    game_mode: str,
    next_piece: Piece,
    best_text: str,
    effects: ScoreEffectManager,
    now_ms: int,
) -> None:
    layout = calculate_layout(screen.get_width(), screen.get_height())
    draw_text_shadow(
        screen,
        f"Score: {score}",
        effects.score_font_size(HUD_SCORE_FONT_SIZE, now_ms),
        HUD_SCORE_TEXT_COLOR,
        layout.hud_x,
        layout.hud_y,
        HUD_SCORE_SHADOW_COLOR,
        HUD_SCORE_SHADOW_OFFSET,
    )
    draw_text_shadow(
        screen,
        f"Level: {get_level(score)}",
        HUD_MODE_FONT_SIZE,
        WHITE,
        layout.hud_x,
        layout.hud_y + max(42, int(46 * layout.scale)),
        HUD_SCORE_SHADOW_COLOR,
        HUD_SCORE_SHADOW_OFFSET,
    )

    side_space = screen.get_width() - (layout.board_x + layout.board_width)
    panel_width = max(112, int(122 * layout.scale))
    panel_height = max(108, int(120 * layout.scale))
    if side_space >= panel_width + 18:
        panel = pygame.Rect(layout.board_x + layout.board_width + 12, layout.board_y + 4, panel_width, panel_height)
    else:
        panel = pygame.Rect(screen.get_width() - panel_width - 10, 12, panel_width, panel_height)
    draw_panel(screen, panel, PANEL_BG, PANEL_BORDER, radius=7)
    draw_text(screen, "Next", 14, MUTED_TEXT, panel.centerx, panel.y + 18)
    preview_rect = pygame.Rect(panel.x + 10, panel.y + 34, panel.width - 20, panel.height - 62)
    occupied = [
        (j, i)
        for i, row in enumerate(next_piece.shape)
        for j, cell in enumerate(row)
        if cell
    ]
    occupied_cols = max(1, max((x for x, _y in occupied), default=0) - min((x for x, _y in occupied), default=0) + 1)
    occupied_rows = max(1, max((y for _x, y in occupied), default=0) - min((y for _x, y in occupied), default=0) + 1)
    preview_block = max(
        9,
        min(layout.block_size - 5, preview_rect.width // occupied_cols, preview_rect.height // occupied_rows),
    )
    next_piece.draw_preview(screen, preview_block, preview_rect, BLACK)
    draw_text(screen, best_text[:24], 12, WHITE, panel.centerx, panel.bottom - 16)
    draw_text_shadow(
        screen,
        f"Mode: {game_mode_label(game_mode)}",
        HUD_MODE_FONT_SIZE,
        WHITE,
        layout.hud_x,
        layout.hud_y + max(22, int(24 * layout.scale)),
        HUD_SCORE_SHADOW_COLOR,
        HUD_SCORE_SHADOW_OFFSET,
    )


def countdown(screen: pygame.Surface, clock: pygame.time.Clock) -> pygame.Surface:
    for value in range(3, 0, -1):
        screen.fill(BLACK)
        draw_text(screen, str(value), 60, WHITE, screen.get_width() // 2, screen.get_height() // 2)
        pygame.display.update()
        started_ms = pygame.time.get_ticks()
        while pygame.time.get_ticks() - started_ms < 1000:
            clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.VIDEORESIZE:
                    screen = handle_resize_event(event)
                    screen.fill(BLACK)
                    draw_text(screen, str(value), 60, WHITE, screen.get_width() // 2, screen.get_height() // 2)
                    pygame.display.update()
    return screen


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
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if play_rect.collidepoint(event.pos):
                    return True
                if menu_rect.collidepoint(event.pos):
                    return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True


def reveal_final_board(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    draw_frame: Callable[[], None],
) -> pygame.Surface:
    started_ms = pygame.time.get_ticks()
    while pygame.time.get_ticks() - started_ms < GAME_OVER_REVEAL_DELAY_MS:
        draw_frame()
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 70))
        screen.blit(overlay, (0, 0))
        pygame.display.update()
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
    return screen


def main_game(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
    score_service: ScoreService,
    open_pause_menu: Callable[[Callable[[], None], int], str | None],
    on_countdown_complete: Callable[[], None] | None = None,
    on_game_over: Callable[[], None] | None = None,
) -> None:
    pygame.key.set_repeat(0)
    while True:
        screen = countdown(screen, clock)
        if on_countdown_complete is not None:
            on_countdown_complete()

        locked: dict[tuple[int, int], int] = {}
        fall_time = 0
        score = 0
        total_lines = 0
        combo_count = 0
        piece_weights = piece_weights_for_mode(state.game_mode)
        piece = Piece.spawn(SHAPES, piece_weights, COLS)
        next_piece = Piece.spawn(SHAPES, piece_weights, COLS)
        effects = ScoreEffectManager()
        key_repeat = KeyRepeatController({})
        single_action_keys_held: set[int] = set()
        running = True
        music_stopped_on_loss = False
        best_text = "Best: -"
        best_queue: "queue.Queue[str]" = queue.Queue()

        def load_best_player() -> None:
            try:
                rows = score_service.get_leaderboard(mode=state.game_mode)
                if rows:
                    best = rows[0]
                    nickname = str(best.get("nickname", "unknown"))
                    best_score = int(best.get("score", 0))
                    best_queue.put(f"Best: {nickname} - {best_score}")
                else:
                    best_queue.put("Best: -")
            except Exception as exc:
                print(f"[score-flow] Best player load failed: {exc.__class__.__name__}")
                best_queue.put("Best: -")

        threading.Thread(target=load_best_player, daemon=True).start()

        def current_grid() -> list[list[int]]:
            return create_grid(locked, ROWS, COLS)

        def spawn_piece() -> Piece:
            return Piece.spawn(SHAPES, piece_weights, COLS)

        def stop_music_on_loss() -> None:
            nonlocal music_stopped_on_loss
            if music_stopped_on_loss or on_game_over is None:
                return
            on_game_over()
            music_stopped_on_loss = True

        def move_piece(dx: int, dy: int) -> bool:
            nonlocal piece
            grid = current_grid()
            if piece.valid_move(dx, dy, grid, COLS, ROWS):
                piece.x += dx
                piece.y += dy
                return True
            return False

        def lock_piece(now_ms: int) -> None:
            nonlocal locked, piece, next_piece, running, score, total_lines, fall_time, combo_count
            for x, y in piece.get_cells():
                locked[(x, y)] = 1

            locked, cleared = clear_full_rows(locked, ROWS, COLS)
            if cleared:
                combo_count += 1
                total_lines += cleared
                base_points = score_for_cleared_lines(cleared)
                points = base_points * combo_count
                score += points
                effects.add_line_clear(
                    points=points,
                    lines=cleared,
                    now_ms=now_ms,
                    x=screen.get_width() // 2,
                    y=screen.get_height() // 2,
                    combo_count=combo_count,
                )
            else:
                combo_count = 0

            piece = next_piece
            next_piece = spawn_piece()
            grid = current_grid()
            if not piece.valid_move(0, 0, grid, COLS, ROWS):
                running = False
                stop_music_on_loss()
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
            nonlocal best_text
            now_ms = pygame.time.get_ticks()
            try:
                best_text = best_queue.get_nowait()
            except queue.Empty:
                pass
            grid = current_grid()
            layout = calculate_layout(screen.get_width(), screen.get_height())
            draw_grid(screen, background_img, grid)
            piece.draw(screen, layout.block_size, WHITE, BLACK, layout.board_x, layout.board_y)
            effects.draw_board_flash(
                screen,
                pygame.Rect(layout.board_x, layout.board_y, layout.board_width, layout.board_height),
                now_ms,
            )
            draw_game_hud(screen, score, state.game_mode, next_piece, best_text, effects, now_ms)
            effects.draw_popups(screen, now_ms)

        while running:
            dt = clock.tick(FPS)
            now_ms = pygame.time.get_ticks()
            fall_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.VIDEORESIZE:
                    screen = handle_resize_event(event)
                    key_repeat.clear()
                    single_action_keys_held.clear()
                    continue
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

            if running and fall_time / 1000 >= get_fall_speed(score):
                if not move_piece(0, 1):
                    lock_piece(now_ms)
                fall_time = 0

            draw_frame()
            pygame.display.update()

        key_repeat.clear()
        single_action_keys_held.clear()
        stop_music_on_loss()
        screen = reveal_final_board(screen, clock, draw_frame)
        submit_queue: "queue.Queue[str]" = queue.Queue()

        def submit_worker() -> None:
            try:
                result = score_service.record_score_result(
                    state.player_name,
                    score,
                    mode=state.game_mode,
                    lines=total_lines,
                    level=get_level(score),
                )
                submit_queue.put(result.message)
            except Exception as exc:
                message = f"Score was not submitted: {exc.__class__.__name__}"
                print(f"[score-flow] Background submission failed: {exc.__class__.__name__}")
                submit_queue.put(message)

        threading.Thread(target=submit_worker, daemon=True).start()
        if not game_over_screen(screen, clock, score, "Submitting Season 2 score...", submit_queue):
            break
