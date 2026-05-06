from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.config import (
    BOARD_MAX_HEIGHT_RATIO,
    BOARD_MAX_WIDTH_RATIO,
    BOARD_MIN_BLOCK_SIZE,
    BOARD_SIDE_PADDING_RATIO,
    COLS,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FONT_SCALE_BASE_HEIGHT,
    RESPONSIVE_PANEL_WIDTH_RATIO,
    MAX_WINDOW_HEIGHT_RATIO,
    MAX_WINDOW_WIDTH_RATIO,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    ROWS,
    UI_SCALE_MAX,
    UI_SCALE_MIN,
)


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    board_x: int
    board_y: int
    board_width: int
    board_height: int
    block_size: int
    hud_x: int
    hud_y: int
    panel_x: int
    panel_y: int
    panel_width: int
    panel_height: int
    scale: float


def clamp_window_size(width: int, height: int) -> tuple[int, int]:
    return max(MIN_WINDOW_WIDTH, int(width)), max(MIN_WINDOW_HEIGHT, int(height))


def initial_window_size() -> tuple[int, int]:
    try:
        display_info = pygame.display.Info()
        display_width = int(display_info.current_w)
        display_height = int(display_info.current_h)
    except pygame.error:
        return DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

    width = int(display_width * MAX_WINDOW_WIDTH_RATIO) if display_width else DEFAULT_WINDOW_WIDTH
    height = int(display_height * MAX_WINDOW_HEIGHT_RATIO) if display_height else DEFAULT_WINDOW_HEIGHT
    return clamp_window_size(width, height)


def calculate_layout(width: int, height: int) -> Layout:
    width, height = clamp_window_size(width, height)
    scale = max(UI_SCALE_MIN, min(UI_SCALE_MAX, height / FONT_SCALE_BASE_HEIGHT))
    side_padding = max(14, int(width * BOARD_SIDE_PADDING_RATIO))
    available_width = max(BOARD_MIN_BLOCK_SIZE * COLS, int(width * BOARD_MAX_WIDTH_RATIO) - side_padding * 2)
    available_height = max(BOARD_MIN_BLOCK_SIZE * ROWS, int(height * BOARD_MAX_HEIGHT_RATIO) - 82)
    block_size = max(BOARD_MIN_BLOCK_SIZE, min(available_width // COLS, available_height // ROWS))
    board_width = block_size * COLS
    board_height = block_size * ROWS
    board_x = (width - board_width) // 2
    board_y = max(78, (height - board_height) // 2 + 26)
    if board_y + board_height > height - 18:
        board_y = max(64, height - board_height - 18)
    panel_width = min(width - 44, max(280, int(width * 0.78)))
    panel_height = min(height - 120, max(220, int(height * 0.48)))
    return Layout(
        width=width,
        height=height,
        board_x=board_x,
        board_y=board_y,
        board_width=board_width,
        board_height=board_height,
        block_size=block_size,
        hud_x=width // 2,
        hud_y=max(26, board_y // 2),
        panel_x=(width - panel_width) // 2,
        panel_y=max(92, (height - panel_height) // 2),
        panel_width=panel_width,
        panel_height=panel_height,
        scale=scale,
    )


def content_rect(
    surface: pygame.Surface,
    max_width: int,
    height: int,
    *,
    y: int | None = None,
    width_ratio: float = RESPONSIVE_PANEL_WIDTH_RATIO,
    min_margin: int = 26,
) -> pygame.Rect:
    available_width = max(1, surface.get_width() - min_margin * 2)
    panel_width = min(max_width, int(surface.get_width() * width_ratio), available_width)
    panel_height = min(height, max(1, surface.get_height() - min_margin * 2))
    rect = pygame.Rect(0, 0, panel_width, panel_height)
    rect.centerx = surface.get_width() // 2
    rect.y = y if y is not None else max(min_margin, (surface.get_height() - panel_height) // 2)
    if rect.bottom > surface.get_height() - min_margin:
        rect.bottom = surface.get_height() - min_margin
    return rect


def scale_font(base_size: int, surface: pygame.Surface | Layout) -> int:
    if isinstance(surface, Layout):
        scale = surface.scale
    else:
        scale = calculate_layout(surface.get_width(), surface.get_height()).scale
    return max(10, int(base_size * scale))


def handle_resize_event(event: pygame.event.Event) -> pygame.Surface:
    width, height = clamp_window_size(getattr(event, "w", MIN_WINDOW_WIDTH), getattr(event, "h", MIN_WINDOW_HEIGHT))
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def toggle_fullscreen(current_windowed_size: tuple[int, int], fullscreen: bool) -> tuple[pygame.Surface, bool, tuple[int, int]]:
    if fullscreen:
        screen = pygame.display.set_mode(current_windowed_size, pygame.RESIZABLE)
        return screen, False, current_windowed_size
    surface = pygame.display.get_surface()
    if surface is not None:
        current_windowed_size = clamp_window_size(surface.get_width(), surface.get_height())
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return screen, True, current_windowed_size
