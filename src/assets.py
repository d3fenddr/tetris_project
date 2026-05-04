from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from src.config import (
    APP_TITLE,
    ASSET_BACKGROUND,
    ASSET_FIRST_PAGE,
    ASSET_GAME_MUSIC,
    ASSET_MENU_MUSIC,
    BLACK,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from src.utils.resource_path import resource_path

@dataclass
class AssetBundle:
    background_img: pygame.Surface
    first_page_img: pygame.Surface
    menu_music_path: str
    game_music_path: str
    audio_available: bool


def initialize_pygame() -> bool:
    pygame.display.init()
    pygame.font.init()
    audio_available = True
    try:
        pygame.mixer.init()
    except pygame.error:
        audio_available = False
    return audio_available


def create_window() -> pygame.Surface:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(APP_TITLE)
    return screen


def _fallback_image(size: Tuple[int, int]) -> pygame.Surface:
    image = pygame.Surface(size)
    image.fill(BLACK)
    return image


def _load_image(path: str, size: Tuple[int, int], warnings: List[str]) -> pygame.Surface:
    try:
        image = pygame.image.load(path).convert()
        return pygame.transform.scale(image, size)
    except pygame.error as exc:
        warnings.append(f"Image load failed: {path} ({exc})")
        return _fallback_image(size)
    except FileNotFoundError:
        warnings.append(f"Image not found: {path}")
        return _fallback_image(size)


def load_assets(audio_available: bool) -> tuple[AssetBundle, List[str]]:
    warnings: List[str] = []
    menu_music_path = resource_path(ASSET_MENU_MUSIC)
    game_music_path = resource_path(ASSET_GAME_MUSIC)
    background_path = resource_path(ASSET_BACKGROUND)
    first_page_path = resource_path(ASSET_FIRST_PAGE)

    background_img = _load_image(background_path, (WINDOW_WIDTH, WINDOW_HEIGHT), warnings)
    first_page_img = _load_image(first_page_path, (WINDOW_WIDTH, WINDOW_HEIGHT), warnings)

    if not os.path.exists(menu_music_path):
        warnings.append(f"Music file not found: {menu_music_path}")
    if not os.path.exists(game_music_path):
        warnings.append(f"Music file not found: {game_music_path}")
    if not audio_available:
        warnings.append("Audio disabled: no available sound device.")

    return (
        AssetBundle(
            background_img=background_img,
            first_page_img=first_page_img,
            menu_music_path=menu_music_path,
            game_music_path=game_music_path,
            audio_available=audio_available,
        ),
        warnings,
    )
