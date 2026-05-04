from __future__ import annotations

from typing import Callable, Optional

import pygame

from src.config import BLACK, BUTTON_DEBOUNCE_MS, FPS, RED, WHITE
from src.utils.ui_helpers import draw_text


def confirm_exit_mouse(screen: pygame.Surface, clock: pygame.time.Clock) -> bool:
    while True:
        screen.fill(BLACK)
        draw_text(screen, "Exit without saving?", 26, WHITE, screen.get_width() // 2, screen.get_height() // 2 - 30)

        mx, my = pygame.mouse.get_pos()
        yes_color = RED if my in range(screen.get_height() // 2, screen.get_height() // 2 + 35) and mx < screen.get_width() // 2 else WHITE
        no_color = RED if my in range(screen.get_height() // 2, screen.get_height() // 2 + 35) and mx > screen.get_width() // 2 else WHITE

        font = pygame.font.SysFont("comicsans", 24)
        yes_surface = font.render("Yes", True, yes_color)
        no_surface = font.render("No", True, no_color)
        yes_rect = yes_surface.get_rect(center=(screen.get_width() // 2 - 80, screen.get_height() // 2 + 20))
        no_rect = no_surface.get_rect(center=(screen.get_width() // 2 + 80, screen.get_height() // 2 + 20))
        screen.blit(yes_surface, yes_rect)
        screen.blit(no_surface, no_rect)

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if yes_rect.collidepoint(event.pos):
                    return True
                if no_rect.collidepoint(event.pos):
                    return False


def pause_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    draw_game_frame: Callable[[], None],
    score: int,
    open_settings_menu: Callable[[], None],
    on_pause_music: Callable[[], None],
    on_unpause_music: Callable[[], None],
    on_stop_music: Callable[[], None],
) -> Optional[str]:
    options = [("Continue", "continue"), ("Settings", "settings"), ("Exit Game", "exit")]
    on_pause_music()
    last_click_ms = 0

    while True:
        draw_game_frame()
        draw_text(screen, f"Score: {score}", 24, WHITE, screen.get_width() // 2, 20)

        mx, my = pygame.mouse.get_pos()
        buttons: list[tuple[pygame.Rect, str]] = []
        for idx, (label, action) in enumerate(options):
            y = screen.get_height() // 2 + idx * 50
            color = RED if abs(my - y) < 20 else WHITE
            rect = draw_text(screen, label, 26, color, screen.get_width() // 2, y)
            buttons.append((rect, action))

        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                on_unpause_music()
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                now = pygame.time.get_ticks()
                if now - last_click_ms < BUTTON_DEBOUNCE_MS:
                    continue
                last_click_ms = now
                for rect, action in buttons:
                    if not rect.collidepoint(event.pos):
                        continue
                    if action == "continue":
                        on_unpause_music()
                        return None
                    if action == "settings":
                        open_settings_menu()
                    elif action == "exit":
                        if confirm_exit_mouse(screen, clock):
                            on_stop_music()
                            return "exit"
