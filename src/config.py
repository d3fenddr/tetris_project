from __future__ import annotations

from typing import List

APP_TITLE = "Tetris"

WINDOW_WIDTH = 350
WINDOW_HEIGHT = 700
ROWS = 20
COLS = 10
BLOCK_SIZE = WINDOW_WIDTH // COLS
FPS = 60

WHITE = (255, 255, 255)
GRAY = (50, 50, 50)
BLUE = (0, 150, 255)
RED = (255, 0, 0)
DARK_RED = (115, 0, 0)
BLACK = (0, 0, 0)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BRONZE = (205, 127, 50)

ASSET_MENU_MUSIC = "menu-music.mp3"
ASSET_GAME_MUSIC = "game-music.mp3"
ASSET_BACKGROUND = "background.png"
ASSET_FIRST_PAGE = "first_page.png"

BASE_MAX_VOLUME = 0.07
DEFAULT_VOLUME_PERCENT = 100
DEFAULT_MUSIC_ENABLED = True
MAX_PLAYER_NAME_LENGTH = 12
BUTTON_DEBOUNCE_MS = 180

GOOGLE_SHEET_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/1bFY8FxdE8gl1qFj3jQm7bta9Pizw_yqkSpm-CqRr2JE/"
    "export?format=csv&gid=469714189"
)
GOOGLE_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSd1IqHQhAawskKNluN1Be9Ey2ULny0OGeUkJ2XP3aFjD0rR-Q/formResponse"
)
GOOGLE_FIELD_NAME = "entry.1969811371"
GOOGLE_FIELD_SCORE = "entry.1726351225"

NETWORK_TIMEOUT_SECONDS = 3.5
NETWORK_RETRIES = 2
NETWORK_BACKOFF_SECONDS = 0.35

SHEET_DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

SHAPES = [
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1], [1, 1]],  # O
    [[0, 1, 1], [1, 1, 0]],  # Z
    [[1, 1, 0], [0, 1, 1]],  # S
    [[1, 1, 1, 1]],  # I
    [
        [1, 0, 1, 1, 1],  # 88
        [1, 0, 1, 0, 0],
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 1],
        [1, 1, 1, 0, 1],
    ],
    [[1, 0], [1, 0], [1, 1]],  # L
    [[0, 1], [0, 1], [1, 1]],  # J
]
SHAPE_WEIGHTS = [100, 100, 100, 100, 100, 35, 100, 100]


def validated_shape_weights() -> List[int]:
    if len(SHAPE_WEIGHTS) == len(SHAPES):
        return SHAPE_WEIGHTS
    return [100] * len(SHAPES)


VALIDATED_SHAPE_WEIGHTS = validated_shape_weights()

