from __future__ import annotations

import pygame

from src.config import (
    BLACK,
    BUTTON_BG,
    BUTTON_BORDER,
    BUTTON_HOVER_BG,
    BUTTON_SELECTED_BG,
    PANEL_BG,
    PANEL_BORDER,
    WHITE,
)
from src.utils.layout import scale_font


def draw_text(
    screen: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    x: int,
    y: int,
) -> pygame.Rect:
    font = pygame.font.SysFont("comicsans", scale_font(size, screen))
    label = font.render(text, True, color)
    rect = label.get_rect(center=(x, y))
    screen.blit(label, rect)
    return rect


def draw_text_shadow(
    screen: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    x: int,
    y: int,
    shadow_color: tuple[int, int, int] = BLACK,
    shadow_offset: int = 2,
) -> pygame.Rect:
    draw_text(screen, text, size, shadow_color, x + shadow_offset, y + shadow_offset)
    return draw_text(screen, text, size, color, x, y)


def draw_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fill_color: tuple[int, int, int] = PANEL_BG,
    border_color: tuple[int, int, int] = PANEL_BORDER,
    radius: int = 8,
) -> None:
    pygame.draw.rect(screen, fill_color, rect, border_radius=radius)
    pygame.draw.rect(screen, border_color, rect, width=1, border_radius=radius)


def draw_button(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font_size: int,
    *,
    hovered: bool = False,
    selected: bool = False,
    enabled: bool = True,
) -> pygame.Rect:
    if selected:
        fill = BUTTON_SELECTED_BG
    elif hovered and enabled:
        fill = BUTTON_HOVER_BG
    else:
        fill = BUTTON_BG
    border = WHITE if selected else BUTTON_BORDER
    text_color = WHITE if enabled else (120, 124, 136)
    pygame.draw.rect(screen, fill, rect, border_radius=8)
    pygame.draw.rect(screen, border, rect, width=1, border_radius=8)
    draw_text(screen, label, font_size, text_color, rect.centerx, rect.centery)
    return rect


def draw_image_cover(screen: pygame.Surface, image: pygame.Surface) -> None:
    target_width, target_height = screen.get_size()
    if image.get_width() <= 0 or image.get_height() <= 0:
        screen.fill(BLACK)
        return
    scale = max(target_width / image.get_width(), target_height / image.get_height())
    scaled_size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
    scaled = pygame.transform.smoothscale(image, scaled_size)
    rect = scaled.get_rect(center=(target_width // 2, target_height // 2))
    screen.blit(scaled, rect)
