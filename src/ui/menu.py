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
from src.services.update_service import BackgroundUpdateChecker
from src.state import AppState
from src.utils.layout import handle_resize_event
from src.utils.ui_helpers import draw_button, draw_image_cover, draw_panel, draw_text, draw_text_shadow
from src.ui.update_prompt import show_update_prompt
from src.version import APP_VERSION


def show_main_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    background_img: pygame.Surface,
    update_checker: BackgroundUpdateChecker | None = None,
) -> str:
    button_labels = ["Play", "Profile", "Leaderboard", "Season 1 Top 3", "History", "Settings", "Exit"]
    last_click_ms = 0
    selected_index = 0

    while True:
        button_width = min(max(MENU_BUTTON_WIDTH, int(screen.get_width() * 0.46)), screen.get_width() - 80)
        button_height = max(MENU_BUTTON_HEIGHT, int(screen.get_height() * 0.052))
        button_gap = max(MENU_BUTTON_GAP, int(screen.get_height() * 0.014))
        total_height = len(button_labels) * button_height + (len(button_labels) - 1) * button_gap
        start_y = max(160, screen.get_height() // 2 - total_height // 2 + 58)
        draw_image_cover(screen, background_img)
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
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.center = (
                screen.get_width() // 2,
                start_y + idx * (button_height + button_gap),
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

        draw_text(screen, f"v{APP_VERSION}", 14, MUTED_TEXT, screen.get_width() - 38, screen.get_height() - 20)
        pygame.display.update()

        if update_checker and not state.update_prompt_seen:
            result = update_checker.result()
            if result:
                state.update_prompt_seen = True
                if result.update_available:
                    show_update_prompt(screen, clock, result)

        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
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
                    continue
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
        draw_image_cover(screen, background_img)
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 150))
        screen.blit(overlay, (0, 0))

        draw_text_shadow(screen, "Choose Mode", MODE_TITLE_FONT_SIZE, WHITE, screen.get_width() // 2, 74)

        mouse_pos = pygame.mouse.get_pos()
        mode_rects: list[tuple[pygame.Rect, str]] = []
        card_width = min(max(MODE_CARD_WIDTH, int(screen.get_width() * 0.62)), screen.get_width() - 64)
        card_height = max(MODE_CARD_HEIGHT, int(screen.get_height() * 0.082))
        card_gap = max(MODE_CARD_GAP, int(screen.get_height() * 0.014))
        total_cards_height = len(GAME_MODE_ORDER) * card_height + (len(GAME_MODE_ORDER) - 1) * card_gap
        cards_start_y = max(150, screen.get_height() // 2 - total_cards_height // 2 + 18)
        for idx, mode in enumerate(GAME_MODE_ORDER):
            y = cards_start_y + idx * (card_height + card_gap)
            label = game_mode_label(mode)
            hit_rect = pygame.Rect(0, 0, card_width, card_height)
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
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
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
