from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.config import DEFAULT_GAME_MODE, DEFAULT_MUSIC_ENABLED, DEFAULT_VOLUME_PERCENT
from src.game.modes import validated_game_mode


@dataclass
class AccountSession:
    username: str
    user_id: Optional[int] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountSession":
        return cls(
            username=str(data.get("username", "")),
            user_id=int(data["user_id"]) if data.get("user_id") is not None else None,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }


@dataclass
class AppState:
    player_name: str = ""
    volume_percent: int = DEFAULT_VOLUME_PERCENT
    music_enabled: bool = DEFAULT_MUSIC_ENABLED
    game_mode: str = DEFAULT_GAME_MODE
    account: Optional[AccountSession] = None
    last_error: str = ""

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> "AppState":
        account_raw = data.get("account")
        account = AccountSession.from_dict(account_raw) if isinstance(account_raw, dict) else None
        game_mode_raw = data.get("game_mode", DEFAULT_GAME_MODE)
        game_mode = game_mode_raw if isinstance(game_mode_raw, str) else DEFAULT_GAME_MODE
        return cls(
            player_name=str(data.get("player_name", "")),
            volume_percent=int(data.get("volume_percent", DEFAULT_VOLUME_PERCENT)),
            music_enabled=bool(data.get("music_enabled", DEFAULT_MUSIC_ENABLED)),
            game_mode=validated_game_mode(game_mode),
            account=account,
        )

    def to_storage(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "player_name": self.player_name,
            "volume_percent": self.volume_percent,
            "music_enabled": self.music_enabled,
            "game_mode": validated_game_mode(self.game_mode),
        }
        payload["account"] = self.account.to_dict() if self.account else None
        return payload
