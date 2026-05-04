from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.config import DEFAULT_MUSIC_ENABLED, DEFAULT_VOLUME_PERCENT


@dataclass
class AccountSession:
    username: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountSession":
        return cls(
            username=str(data.get("username", "")),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }


@dataclass
class AppState:
    player_name: str = ""
    volume_percent: int = DEFAULT_VOLUME_PERCENT
    music_enabled: bool = DEFAULT_MUSIC_ENABLED
    account: Optional[AccountSession] = None
    last_error: str = ""

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> "AppState":
        account_raw = data.get("account")
        account = AccountSession.from_dict(account_raw) if isinstance(account_raw, dict) else None
        return cls(
            player_name=str(data.get("player_name", "")),
            volume_percent=int(data.get("volume_percent", DEFAULT_VOLUME_PERCENT)),
            music_enabled=bool(data.get("music_enabled", DEFAULT_MUSIC_ENABLED)),
            account=account,
        )

    def to_storage(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "player_name": self.player_name,
            "volume_percent": self.volume_percent,
            "music_enabled": self.music_enabled,
        }
        payload["account"] = self.account.to_dict() if self.account else None
        return payload

