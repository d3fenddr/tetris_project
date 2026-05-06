from __future__ import annotations

import pygame

from src.config import BLACK, BRONZE, GOLD, SILVER, WHITE
from src.services.rewards import SeasonReward
from src.utils.ui_helpers import draw_text


MEDAL_COLORS = {
    "gold": GOLD,
    "silver": SILVER,
    "bronze": BRONZE,
}


def draw_medal_badge(
    screen: pygame.Surface,
    reward: SeasonReward,
    x: int,
    y: int,
    radius: int = 12,
    *,
    show_rank: bool = False,
) -> None:
    color = MEDAL_COLORS.get(reward.medal, WHITE)
    pygame.draw.circle(screen, color, (x, y), radius)
    pygame.draw.circle(screen, WHITE, (x, y), radius, 1)
    pygame.draw.circle(screen, BLACK, (x, y), max(2, radius - 5), 1)
    if show_rank:
        draw_text(screen, str(reward.rank), max(10, radius + 1), BLACK, x, y - 1)
