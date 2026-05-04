from __future__ import annotations

import pygame


def draw_text(
    screen: pygame.Surface,
    text: str,
    size: int,
    color: tuple[int, int, int],
    x: int,
    y: int,
) -> pygame.Rect:
    font = pygame.font.SysFont("comicsans", size)
    label = font.render(text, True, color)
    rect = label.get_rect(center=(x, y))
    screen.blit(label, rect)
    return rect

