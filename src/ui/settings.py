from __future__ import annotations

from typing import Callable

import pygame

from src.config import (
    BLACK,
    BUTTON_DEBOUNCE_MS,
    FPS,
    MENU_BUTTON_HEIGHT,
    MENU_BUTTON_WIDTH,
    MUTED_TEXT,
    PANEL_BG,
    PANEL_BORDER,
    RED,
    SETTINGS_PANEL_MAX_WIDTH,
    WHITE,
)
from src.services.update_service import BackgroundUpdateChecker
from src.state import AppState
from src.utils.layout import content_rect, handle_resize_event
from src.utils.ui_helpers import draw_button, draw_panel, draw_text, draw_text_shadow
from src.ui.update_prompt import show_update_prompt
from src.version import APP_VERSION


def settings_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    apply_volume: Callable[[], None],
    on_state_changed: Callable[[], None],
    update_checker: BackgroundUpdateChecker | None = None,
) -> None:
    last_click_ms = 0
    update_status = ""
    manual_check_pending = False

    def change_volume(delta: int) -> None:
        state.volume_percent = min(100, max(0, state.volume_percent + delta))
        apply_volume()
        on_state_changed()

    def toggle_music() -> None:
        state.music_enabled = not state.music_enabled
        apply_volume()
        on_state_changed()

    while True:
        screen.fill(BLACK)
        draw_text_shadow(screen, "Settings", 36, WHITE, screen.get_width() // 2, 62)

        panel = content_rect(screen, SETTINGS_PANEL_MAX_WIDTH, 390, y=112)
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        draw_text(screen, "Audio", 24, WHITE, panel.centerx, panel.y + 38)
        draw_text(screen, "Music Volume", 16, MUTED_TEXT, panel.centerx, panel.y + 82)
        draw_text(screen, f"{state.volume_percent}%", 34, WHITE, panel.centerx, panel.y + 122)

        bar_rect = pygame.Rect(panel.x + 40, panel.y + 154, panel.width - 80, 12)
        pygame.draw.rect(screen, (18, 20, 28), bar_rect, border_radius=6)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * (state.volume_percent / 100))
        pygame.draw.rect(screen, RED, fill_rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_BORDER, bar_rect, width=1, border_radius=6)

        mouse_pos = pygame.mouse.get_pos()
        minus_rect = pygame.Rect(panel.x + 45, panel.y + 190, 72, 38)
        plus_rect = pygame.Rect(panel.right - 117, panel.y + 190, 72, 38)
        toggle_rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
        toggle_rect.center = (panel.centerx, panel.y + 260)
        update_rect = pygame.Rect(0, 0, MENU_BUTTON_WIDTH, MENU_BUTTON_HEIGHT)
        update_rect.center = (panel.centerx, panel.y + 332)

        draw_button(screen, minus_rect, "-10", 20, hovered=minus_rect.collidepoint(mouse_pos))
        draw_button(screen, plus_rect, "+10", 20, hovered=plus_rect.collidepoint(mouse_pos))
        draw_button(
            screen,
            toggle_rect,
            f"Music: {'On' if state.music_enabled else 'Off'}",
            21,
            hovered=toggle_rect.collidepoint(mouse_pos),
            selected=state.music_enabled,
        )
        draw_text(screen, f"Version v{APP_VERSION}", 15, MUTED_TEXT, panel.centerx, panel.y + 300)
        draw_button(
            screen,
            update_rect,
            "Checking..." if manual_check_pending else "Check for updates",
            18,
            hovered=update_rect.collidepoint(mouse_pos),
            enabled=update_checker is not None and not manual_check_pending,
        )
        if update_status:
            draw_text(screen, update_status, 14, MUTED_TEXT, panel.centerx, panel.y + 372)

        draw_text(screen, "LEFT/RIGHT volume   M music   ESC back", 14, MUTED_TEXT, screen.get_width() // 2, screen.get_height() - 28)
        pygame.display.update()

        if update_checker and manual_check_pending:
            result = update_checker.result()
            if result:
                manual_check_pending = False
                if result.update_available:
                    update_status = "Update available."
                    show_update_prompt(screen, clock, result)
                elif result.error:
                    update_status = "Could not check for updates."
                else:
                    update_status = "You are using the latest version."

        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    change_volume(-10)
                elif event.key == pygame.K_RIGHT:
                    change_volume(10)
                elif event.key == pygame.K_m:
                    toggle_music()
                elif event.key == pygame.K_ESCAPE:
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                if minus_rect.collidepoint(event.pos):
                    change_volume(-10)
                elif plus_rect.collidepoint(event.pos):
                    change_volume(10)
                elif toggle_rect.collidepoint(event.pos):
                    toggle_music()
                elif update_rect.collidepoint(event.pos) and update_checker and not manual_check_pending:
                    update_checker.start(force=True)
                    manual_check_pending = True
                    update_status = ""
