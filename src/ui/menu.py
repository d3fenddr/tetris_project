from __future__ import annotations

import pygame

from src.config import (
    BLACK,
    BUTTON_DEBOUNCE_MS,
    FPS,
    GRAY,
    MAX_PLAYER_NAME_LENGTH,
    RED,
    WHITE,
)
from src.state import AppState
from src.utils.ui_helpers import draw_text


def ensure_player_name(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    first_page_img: pygame.Surface,
) -> None:
    entering = True
    while entering:
        screen.blit(first_page_img, (0, 0))
        draw_text(screen, "Enter name:", 30, WHITE, screen.get_width() // 2, screen.get_height() // 3)
        draw_text(screen, state.player_name or "_", 30, RED, screen.get_width() // 2, screen.get_height() // 2)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and state.player_name.strip():
                    entering = False
                elif event.key == pygame.K_BACKSPACE:
                    state.player_name = state.player_name[:-1]
                else:
                    char = event.unicode
                    if char.isalnum() and len(state.player_name) < MAX_PLAYER_NAME_LENGTH:
                        state.player_name += char


def show_main_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
) -> str:
    button_labels = ["Play", "History", "Settings", "Leaderboard", "Exit"]
    font_size = 32
    spacing = 70
    total_height = len(button_labels) * spacing
    start_y = screen.get_height() // 2 - total_height // 2 + 100

    buttons = [
        (label, font_size, screen.get_width() // 2, start_y + idx * spacing)
        for idx, label in enumerate(button_labels)
    ]
    last_click_ms = 0

    while True:
        screen.blit(background_img, (0, 0))
        draw_text(screen, f"Hello, {state.player_name}", 28, WHITE, screen.get_width() // 2, screen.get_height() // 4)
        draw_text(
            screen,
            "Use arrows to move",
            20,
            WHITE,
            screen.get_width() // 2,
            screen.get_height() // 4 + 40,
        )

        mouse_x, mouse_y = pygame.mouse.get_pos()
        button_rects: list[tuple[str, pygame.Rect]] = []
        for label, size, cx, cy in buttons:
            font = pygame.font.SysFont("comicsans", size)
            text_width, text_height = font.size(label)
            hovered = abs(mouse_x - cx) < text_width // 2 and abs(mouse_y - cy) < text_height // 2
            color = RED if hovered else WHITE
            text_surface = font.render(label, True, color)
            rect = text_surface.get_rect(center=(cx, cy))
            screen.blit(text_surface, rect)
            button_rects.append((label, rect))

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                for label, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        return label.lower()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "exit"

