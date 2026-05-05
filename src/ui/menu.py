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
from src.config import GAME_MODE_ORDER
from src.game.modes import game_mode_description, game_mode_label, next_game_mode
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
    button_labels = ["Play", "Leaderboard", "Season 1 Top 3", "History", "Profile", "Settings", "Exit"]
    font_size = 25
    spacing = 52
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
        account_label = state.account.username if state.account else "Guest"
        draw_text(screen, f"Account: {account_label}", 16, GRAY, screen.get_width() // 2, screen.get_height() // 4 + 34)
        draw_text(screen, f"Mode: {game_mode_label(state.game_mode)}", 16, GRAY, screen.get_width() // 2, screen.get_height() // 4 + 56)

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


def show_game_mode_selector(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
) -> str | None:
    selected_mode = state.game_mode
    selected_index = GAME_MODE_ORDER.index(selected_mode) if selected_mode in GAME_MODE_ORDER else 0
    last_click_ms = 0

    while True:
        selected_mode = GAME_MODE_ORDER[selected_index]
        screen.blit(background_img, (0, 0))
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        draw_text(screen, "Choose Mode", 36, WHITE, screen.get_width() // 2, 75)
        draw_text(screen, "Click a mode or use UP/DOWN / W/S", 18, GRAY, screen.get_width() // 2, 118)
        draw_text(screen, "ENTER to start", 18, GRAY, screen.get_width() // 2, 142)

        mouse_pos = pygame.mouse.get_pos()
        mode_rects: list[tuple[pygame.Rect, str]] = []
        for idx, mode in enumerate(GAME_MODE_ORDER):
            y = 225 + idx * 56
            label = game_mode_label(mode)
            font = pygame.font.SysFont("comicsans", 32 if mode == selected_mode else 24)
            text_width, text_height = font.size(label)
            hit_rect = pygame.Rect(0, 0, max(210, text_width + 38), text_height + 18)
            hit_rect.center = (screen.get_width() // 2, y)
            hovered = hit_rect.collidepoint(mouse_pos)
            if hovered:
                selected_index = idx
                selected_mode = mode
            is_selected = mode == selected_mode
            color = RED if is_selected else WHITE
            size = 32 if is_selected else 24
            if is_selected:
                pygame.draw.rect(screen, (0, 0, 0), hit_rect.inflate(16, 4), border_radius=6)
                pygame.draw.rect(screen, RED, hit_rect.inflate(16, 4), width=1, border_radius=6)
            draw_text(screen, label, size, color, screen.get_width() // 2, y)
            mode_rects.append((hit_rect, mode))

        draw_text(
            screen,
            game_mode_description(selected_mode),
            18,
            WHITE,
            screen.get_width() // 2,
            screen.get_height() - 112,
        )
        draw_text(screen, "ESC to return", 18, GRAY, screen.get_width() // 2, screen.get_height() - 55)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.MOUSEMOTION:
                for idx, (rect, mode) in enumerate(mode_rects):
                    if rect.collidepoint(event.pos):
                        selected_mode = mode
                        selected_index = idx
                        break
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                for rect, mode in mode_rects:
                    if rect.collidepoint(event.pos):
                        return mode
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_mode = next_game_mode(selected_mode, -1)
                    selected_index = GAME_MODE_ORDER.index(selected_mode)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_mode = next_game_mode(selected_mode, 1)
                    selected_index = GAME_MODE_ORDER.index(selected_mode)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return selected_mode
                elif event.key == pygame.K_ESCAPE:
                    return None
