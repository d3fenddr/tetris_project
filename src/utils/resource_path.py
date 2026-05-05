from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
ASSETS_DIR = RUNTIME_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
MUSIC_DIR = ASSETS_DIR / "audio" / "music"
SOUNDS_DIR = ASSETS_DIR / "audio" / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"


def resource_path(relative_path: str | Path) -> str:
    return str(RUNTIME_ROOT / relative_path)


def asset_path(*parts: str) -> str:
    return str(ASSETS_DIR.joinpath(*parts))
