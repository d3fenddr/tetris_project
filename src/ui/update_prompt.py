from __future__ import annotations

import webbrowser

import pygame

from src.config import BUTTON_DEBOUNCE_MS, FPS, MUTED_TEXT, PANEL_BG, PANEL_BORDER, RED, WHITE
from src.services.update_service import UpdateCheckResult
from src.utils.layout import content_rect, handle_resize_event
from src.utils.ui_helpers import draw_button, draw_panel, draw_text, draw_text_shadow


def open_update_url(result: UpdateCheckResult) -> None:
    url = result.download_url or result.release_url
    if not url:
        return
    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"Could not open update URL: {exc.__class__.__name__}")


def show_update_prompt(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    result: UpdateCheckResult,
    *,
    latest_message: str | None = None,
) -> None:
    last_click_ms = 0

    while True:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        panel = content_rect(screen, 520, 310, y=max(120, screen.get_height() // 2 - 155))
        draw_panel(screen, panel, PANEL_BG, PANEL_BORDER)
        title = "Update available" if result.update_available else "Updates"
        draw_text_shadow(screen, title, 31, WHITE, panel.centerx, panel.y + 44)

        if result.update_available:
            draw_text(screen, f"Current version: v{result.current_version}", 18, MUTED_TEXT, panel.centerx, panel.y + 100)
            draw_text(screen, f"Latest version: v{result.latest_version}", 18, WHITE, panel.centerx, panel.y + 130)
            message = latest_message or "Download the latest release when you are ready."
        elif result.error:
            draw_text(screen, "Could not check for updates.", 19, WHITE, panel.centerx, panel.y + 112)
            message = "Please try again later."
        else:
            draw_text(screen, f"Current version: v{result.current_version}", 18, WHITE, panel.centerx, panel.y + 112)
            message = latest_message or "You are using the latest version."

        draw_text(screen, message, 16, MUTED_TEXT, panel.centerx, panel.y + 166)

        mouse_pos = pygame.mouse.get_pos()
        button_width = min(190, max(120, (panel.width - 72) // 2))
        left_rect = pygame.Rect(0, 0, button_width, 42)
        right_rect = pygame.Rect(0, 0, button_width, 42)
        left_rect.center = (panel.centerx - button_width // 2 - 12, panel.y + 242)
        right_rect.center = (panel.centerx + button_width // 2 + 12, panel.y + 242)

        if result.update_available:
            draw_button(screen, left_rect, "Download update", 18, hovered=left_rect.collidepoint(mouse_pos), selected=True)
            draw_button(screen, right_rect, "Later", 18, hovered=right_rect.collidepoint(mouse_pos))
        else:
            ok_rect = pygame.Rect(0, 0, button_width, 42)
            ok_rect.center = (panel.centerx, panel.y + 242)
            draw_button(screen, ok_rect, "OK", 18, hovered=ok_rect.collidepoint(mouse_pos), selected=True)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.VIDEORESIZE:
                screen = handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if result.update_available:
                        open_update_url(result)
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                if result.update_available:
                    if left_rect.collidepoint(event.pos):
                        open_update_url(result)
                        return
                    if right_rect.collidepoint(event.pos):
                        return
                elif ok_rect.collidepoint(event.pos):
                    return
