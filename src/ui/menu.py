from __future__ import annotations

import pygame

from src.config import (
    BUTTON_DEBOUNCE_MS,
    FPS,
    MENU_BUTTON_FONT_SIZE,
    MENU_BUTTON_GAP,
    MENU_BUTTON_HEIGHT,
    MENU_BUTTON_WIDTH,
    MENU_PRIMARY_TEXT_COLOR,
    MENU_SEASON_TITLE_FONT_SIZE,
    MENU_TOP_Y,
    MODE_CARD_GAP,
    MODE_CARD_HEIGHT,
    MODE_CARD_WIDTH,
    MODE_DESCRIPTION_FONT_SIZE,
    MODE_NAME_FONT_SIZE,
    MODE_TITLE_FONT_SIZE,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    RED,
    WHITE,
)
from src.config import GAME_MODE_ORDER
from src.game.modes import game_mode_description, game_mode_label, next_game_mode
from src.state import AppState
from src.utils.ui_helpers import draw_button, draw_panel, draw_text, draw_text_shadow


def show_main_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
) -> str:
    button_labels = ["Play", "Profile", "Leaderboard", "Season 1 Top 3", "History", "Settings", "Exit"]
    start_y = 208
    last_click_ms = 0
    selected_index = 0

    while True:
        screen.blit(background_img, (0, 0))
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 132))
        screen.blit(overlay, (0, 0))
        draw_text_shadow(
            screen,
            "SEASON 2",
            MENU_SEASON_TITLE_FONT_SIZE,
            MENU_PRIMARY_TEXT_COLOR,
            screen.get_width() // 2,
            MENU_TOP_Y,
        )

        mouse_x, mouse_y = pygame.mouse.get_pos()
        button_rects: list[tuple[str, pygame.Rect]] = []
        for idx, label in enumerate(button_labels):
            rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
            rect.center = (
                screen.get_width() // 2,
                start_y + idx * (MENU_BUTTON_HEIGHT + MENU_BUTTON_GAP),
            )
            hovered = rect.collidepoint(mouse_x, mouse_y)
            if hovered:
                selected_index = idx
            draw_button(
                screen,
                rect,
                label,
                MENU_BUTTON_FONT_SIZE,
                hovered=hovered,
                selected=idx == selected_index,
            )
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
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "exit"
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(button_labels)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(button_labels)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return button_labels[selected_index].lower()


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
        overlay.fill((8, 10, 16, 150))
        screen.blit(overlay, (0, 0))

        draw_text_shadow(screen, "Choose Mode", MODE_TITLE_FONT_SIZE, WHITE, screen.get_width() // 2, 74)

        mouse_pos = pygame.mouse.get_pos()
        mode_rects: list[tuple[pygame.Rect, str]] = []
        for idx, mode in enumerate(GAME_MODE_ORDER):
            y = 162 + idx * (MODE_CARD_HEIGHT + MODE_CARD_GAP)
            label = game_mode_label(mode)
            hit_rect = pygame.Rect(0, 0, MODE_CARD_WIDTH, MODE_CARD_HEIGHT)
            hit_rect.center = (screen.get_width() // 2, y)
            hovered = hit_rect.collidepoint(mouse_pos)
            if hovered:
                selected_index = idx
                selected_mode = mode
            is_selected = mode == selected_mode
            fill = (48, 18, 24) if is_selected else PANEL_BG
            border = RED if is_selected else PANEL_BORDER
            draw_panel(screen, hit_rect, fill, border, radius=8)
            draw_text(screen, label, MODE_NAME_FONT_SIZE, WHITE, screen.get_width() // 2, y - 13)
            draw_text(
                screen,
                game_mode_description(mode),
                MODE_DESCRIPTION_FONT_SIZE,
                MUTED_TEXT,
                screen.get_width() // 2,
                y + 16,
            )
            mode_rects.append((hit_rect, mode))

        draw_text(screen, "ESC to return", 17, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 35)

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
