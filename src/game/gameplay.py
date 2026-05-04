from __future__ import annotations

from typing import Callable

import pygame

from src.config import (
    BLACK,
    BLOCK_SIZE,
    COLS,
    DARK_RED,
    FPS,
    GRAY,
    RED,
    ROWS,
    SHAPES,
    VALIDATED_SHAPE_WEIGHTS,
    WHITE,
)
from src.game.board import clear_full_rows, create_grid
from src.game.piece import Piece
from src.game.scoring import score_for_cleared_lines
from src.services.score_service import ScoreService
from src.state import AppState
from src.utils.ui_helpers import draw_text


def draw_grid(screen: pygame.Surface, background_img: pygame.Surface, grid: list[list[int]]) -> None:
    screen.blit(background_img, (0, 0))
    width, height = screen.get_size()
    for y in range(ROWS):
        for x in range(COLS):
            if grid[y][x]:
                pygame.draw.rect(
                    screen,
                    DARK_RED,
                    (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                )
    for y in range(ROWS + 1):
        pygame.draw.line(screen, GRAY, (0, y * BLOCK_SIZE), (width, y * BLOCK_SIZE), 1)
    for x in range(COLS + 1):
        pygame.draw.line(screen, GRAY, (x * BLOCK_SIZE, 0), (x * BLOCK_SIZE, height), 1)
    pygame.draw.rect(screen, GRAY, (0, 0, width, height), 2)


def countdown(screen: pygame.Surface, clock: pygame.time.Clock) -> None:
    for value in range(3, 0, -1):
        screen.fill(BLACK)
        draw_text(screen, str(value), 60, WHITE, screen.get_width() // 2, screen.get_height() // 2)
        pygame.display.update()
        clock.tick(1)


def game_over_screen(screen: pygame.Surface, clock: pygame.time.Clock, score: int) -> bool:
    while True:
        screen.fill(BLACK)
        draw_text(screen, "GAME OVER", 45, RED, screen.get_width() // 2, screen.get_height() // 3)
        draw_text(screen, f"Score: {score}", 28, WHITE, screen.get_width() // 2, screen.get_height() // 3 + 60)
        play_rect = pygame.Rect(screen.get_width() // 2 - 75, screen.get_height() // 2, 150, 40)
        menu_rect = pygame.Rect(screen.get_width() // 2 - 75, screen.get_height() // 2 + 60, 150, 40)
        pygame.draw.rect(screen, GRAY, play_rect)
        pygame.draw.rect(screen, GRAY, menu_rect)
        draw_text(screen, "Play Again", 30, BLACK, play_rect.centerx, play_rect.centery)
        draw_text(screen, "Main Menu", 30, BLACK, menu_rect.centerx, menu_rect.centery)
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
) -> None:
    while True:
        countdown(screen, clock)

        locked: dict[tuple[int, int], int] = {}
        fall_time = 0
        move_delay = 0
        fall_speed = 1.0
        score = 0
        piece = Piece.spawn(SHAPES, VALIDATED_SHAPE_WEIGHTS, COLS)
        running = True

        while running:
            dt = clock.tick(FPS)
            fall_time += dt
            move_delay += dt
            grid = create_grid(locked, ROWS, COLS)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN] and move_delay > 50:
                if piece.valid_move(0, 1, grid, COLS, ROWS):
                    piece.y += 1
                move_delay = 0

            if fall_time / 1000 >= fall_speed:
                if piece.valid_move(0, 1, grid, COLS, ROWS):
                    piece.y += 1
                else:
                    for x, y in piece.get_cells():
                        locked[(x, y)] = 1
                    locked, cleared = clear_full_rows(locked, ROWS, COLS)
                    score += score_for_cleared_lines(cleared)
                    piece = Piece.spawn(SHAPES, VALIDATED_SHAPE_WEIGHTS, COLS)
                    grid = create_grid(locked, ROWS, COLS)
                    if not piece.valid_move(0, 0, grid, COLS, ROWS):
                        running = False
                fall_time = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT and piece.valid_move(-1, 0, grid, COLS, ROWS):
                        piece.x -= 1
                    elif event.key == pygame.K_RIGHT and piece.valid_move(1, 0, grid, COLS, ROWS):
                        piece.x += 1
                    elif event.key == pygame.K_UP:
                        piece.rotate(grid, COLS, ROWS)
                    elif event.key == pygame.K_ESCAPE:
                        def draw_frame() -> None:
                            draw_grid(screen, background_img, grid)
                            piece.draw(screen, BLOCK_SIZE, WHITE, BLACK)

                        result = open_pause_menu(draw_frame, score)
                        if result == "exit":
                            return

            draw_grid(screen, background_img, grid)
            piece.draw(screen, BLOCK_SIZE, WHITE, BLACK)
            draw_text(screen, f"Score: {score}", 24, WHITE, screen.get_width() // 2, 20)
            pygame.display.update()

        score_service.record_score(state.player_name, score)
        if not game_over_screen(screen, clock, score):
            break
