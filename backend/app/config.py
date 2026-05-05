from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("TETRIS_DATABASE_URL", "sqlite:///./tetris.db")
    secret_key: str = os.getenv("TETRIS_SECRET_KEY", "change-me-before-production")
    access_token_expire_minutes: int = _env_int("TETRIS_ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    refresh_token_expire_days: int = _env_int("TETRIS_REFRESH_TOKEN_EXPIRE_DAYS", 14)
    current_season: int = _env_int("TETRIS_CURRENT_SEASON", 2)
    archived_season: int = _env_int("TETRIS_ARCHIVED_SEASON", 1)
    similar_nickname_threshold: float = float(os.getenv("TETRIS_SIMILAR_NICKNAME_THRESHOLD", "0.85"))
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_auth_max_age_seconds: int = _env_int("TELEGRAM_AUTH_MAX_AGE_SECONDS", 3600)
    app_version: str = os.getenv("TETRIS_APP_VERSION", "0.1.0")
    debug_online_score_flow: bool = _env_bool("DEBUG_ONLINE_SCORE_FLOW", True)


settings = Settings()
