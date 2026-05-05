from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.config import (
    BOARD_FLASH_COLOR,
    BOARD_FLASH_DURATION_MS,
    BOARD_FLASH_MAX_ALPHA,
    BOARD_FLASH_WIDTH,
    COMBO_DISPLAY_DURATION_MS,
    COMBO_WINDOW_MS,
    SCORE_EFFECTS_ENABLED,
    SCORE_POPUP_COLOR,
    SCORE_POPUP_COMBO_COLOR,
    SCORE_POPUP_DURATION_MS,
    SCORE_POPUP_FONT_SIZE,
    SCORE_POPUP_LINE_CLEAR_COLOR,
    SCORE_POPUP_LINE_CLEAR_FONT_SIZE,
    SCORE_POPUP_MAX_ACTIVE,
    SCORE_POPUP_RISE_PIXELS,
    SCORE_PULSE_DURATION_MS,
    SCORE_PULSE_SCALE,
)


@dataclass
class ScorePopup:
    text: str
    x: int
    y: int
    color: tuple[int, int, int]
    font_size: int
    start_ms: int
    duration_ms: int
    rise_pixels: int = SCORE_POPUP_RISE_PIXELS

    def alive(self, now_ms: int) -> bool:
        return now_ms - self.start_ms < self.duration_ms

    def draw(self, screen: pygame.Surface, now_ms: int) -> None:
        age = max(0, now_ms - self.start_ms)
        progress = min(1.0, age / self.duration_ms)
        y = self.y - int(self.rise_pixels * progress)
        alpha = max(0, int(255 * (1.0 - progress)))

        font = pygame.font.SysFont("comicsans", self.font_size)
        surface = font.render(self.text, True, self.color)
        surface.set_alpha(alpha)
        rect = surface.get_rect(center=(self.x, y))
        screen.blit(surface, rect)


class ScoreEffectManager:
    def __init__(self) -> None:
        self.popups: list[ScorePopup] = []
        self.board_flash_start_ms: int | None = None
        self.score_pulse_start_ms: int | None = None
        self.combo_count = 0
        self.last_line_clear_ms = -COMBO_WINDOW_MS

    def reset(self) -> None:
        self.popups.clear()
        self.board_flash_start_ms = None
        self.score_pulse_start_ms = None
        self.combo_count = 0
        self.last_line_clear_ms = -COMBO_WINDOW_MS

    def _add_popup(self, popup: ScorePopup) -> None:
        if not SCORE_EFFECTS_ENABLED:
            return
        self.popups.append(popup)
        self.popups = self.popups[-SCORE_POPUP_MAX_ACTIVE:]

    def add_score(self, points: int, now_ms: int, x: int, y: int) -> None:
        if points <= 0:
            return
        self.score_pulse_start_ms = now_ms
        self._add_popup(
            ScorePopup(
                text=f"+{points}",
                x=x,
                y=y,
                color=SCORE_POPUP_COLOR,
                font_size=SCORE_POPUP_FONT_SIZE,
                start_ms=now_ms,
                duration_ms=SCORE_POPUP_DURATION_MS,
            )
        )

    def add_line_clear(self, points: int, lines: int, now_ms: int, x: int, y: int) -> None:
        if points <= 0 or lines <= 0:
            return

        self.score_pulse_start_ms = now_ms
        self.board_flash_start_ms = now_ms
        if now_ms - self.last_line_clear_ms <= COMBO_WINDOW_MS:
            self.combo_count += 1
        else:
            self.combo_count = 1
        self.last_line_clear_ms = now_ms

        label = f"{lines} line{'s' if lines != 1 else ''} +{points}"
        self._add_popup(
            ScorePopup(
                text=label,
                x=x,
                y=y,
                color=SCORE_POPUP_LINE_CLEAR_COLOR,
                font_size=SCORE_POPUP_LINE_CLEAR_FONT_SIZE,
                start_ms=now_ms,
                duration_ms=SCORE_POPUP_DURATION_MS,
            )
        )

        if self.combo_count > 1:
            self._add_popup(
                ScorePopup(
                    text=f"Combo x{self.combo_count}",
                    x=x,
                    y=y + 34,
                    color=SCORE_POPUP_COMBO_COLOR,
                    font_size=SCORE_POPUP_FONT_SIZE,
                    start_ms=now_ms,
                    duration_ms=COMBO_DISPLAY_DURATION_MS,
                    rise_pixels=SCORE_POPUP_RISE_PIXELS // 2,
                )
            )

    def score_font_size(self, base_size: int, now_ms: int) -> int:
        if not SCORE_EFFECTS_ENABLED or self.score_pulse_start_ms is None:
            return base_size

        age = now_ms - self.score_pulse_start_ms
        if age >= SCORE_PULSE_DURATION_MS:
            self.score_pulse_start_ms = None
            return base_size

        progress = age / SCORE_PULSE_DURATION_MS
        scale = 1 + (SCORE_PULSE_SCALE - 1) * (1 - progress)
        return max(base_size, int(base_size * scale))

    def draw_board_flash(self, screen: pygame.Surface, rect: pygame.Rect, now_ms: int) -> None:
        if not SCORE_EFFECTS_ENABLED or self.board_flash_start_ms is None:
            return

        age = now_ms - self.board_flash_start_ms
        if age >= BOARD_FLASH_DURATION_MS:
            self.board_flash_start_ms = None
            return

        progress = age / BOARD_FLASH_DURATION_MS
        alpha = max(0, int(BOARD_FLASH_MAX_ALPHA * (1 - progress)))
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            overlay,
            (*BOARD_FLASH_COLOR, alpha),
            overlay.get_rect(),
            width=BOARD_FLASH_WIDTH,
        )
        screen.blit(overlay, rect.topleft)

    def draw_popups(self, screen: pygame.Surface, now_ms: int) -> None:
        if not SCORE_EFFECTS_ENABLED:
            return

        self.popups = [popup for popup in self.popups if popup.alive(now_ms)]
        for popup in self.popups:
            popup.draw(screen, now_ms)
