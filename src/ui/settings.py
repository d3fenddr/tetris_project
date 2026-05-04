from __future__ import annotations

from typing import Callable

import pygame

from src.config import BLACK, GRAY, RED, WHITE, FPS
from src.state import AppState
from src.utils.ui_helpers import draw_text


def settings_menu(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    state: AppState,
    apply_volume: Callable[[], None],
    on_state_changed: Callable[[], None],
) -> None:
    while True:
        screen.fill(BLACK)
        draw_text(screen, "Settings", 36, WHITE, screen.get_width() // 2, 80)
        draw_text(
            screen,
            f"Music Volume: {state.volume_percent}%",
            28,
            WHITE,
            screen.get_width() // 2,
            200,
        )
        draw_text(screen, "LEFT/RIGHT to adjust", 20, GRAY, screen.get_width() // 2, 235)
        draw_text(
            screen,
            f"Music: {'On' if state.music_enabled else 'Off'} (Press M)",
            28,
            WHITE,
            screen.get_width() // 2,
            300,
        )
        draw_text(screen, "ESC to return", 20, GRAY, screen.get_width() // 2, screen.get_height() - 20)
        pygame.display.update()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    state.volume_percent = max(0, state.volume_percent - 10)
                    apply_volume()
                    on_state_changed()
                elif event.key == pygame.K_RIGHT:
                    state.volume_percent = min(100, state.volume_percent + 10)
                    apply_volume()
                    on_state_changed()
                elif event.key == pygame.K_m:
                    state.music_enabled = not state.music_enabled
                    apply_volume()
                    on_state_changed()
                elif event.key == pygame.K_ESCAPE:
                    return
