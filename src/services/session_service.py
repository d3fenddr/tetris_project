from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.config import DEFAULT_GAME_MODE


DEFAULT_SESSION_DATA: Dict[str, Any] = {
    "volume_percent": 100,
    "music_enabled": True,
    "game_mode": DEFAULT_GAME_MODE,
    "player_name": "",
    "account": None,
    "pending_scores": [],
    "local_history": [],
    "cached_leaderboard": [],
    "cached_history_by_name": {},
}


class SessionService:
    def __init__(self, session_path: Path | None = None) -> None:
        if session_path is not None:
            self.session_path = session_path
        else:
            app_data = os.getenv("APPDATA")
            if app_data:
                root = Path(app_data) / "tetris"
            else:
                root = Path.home() / ".tetris"
            self.session_path = root / "session.json"
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.session_path.exists():
            return DEFAULT_SESSION_DATA.copy()
        try:
            with self.session_path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
                if not isinstance(loaded, dict):
                    return DEFAULT_SESSION_DATA.copy()
                data = DEFAULT_SESSION_DATA.copy()
                data.update(loaded)
                return data
        except (OSError, json.JSONDecodeError):
            return DEFAULT_SESSION_DATA.copy()

    def save(self, data: Dict[str, Any]) -> None:
        payload = DEFAULT_SESSION_DATA.copy()
        payload.update(data)
        temp_path = self.session_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        temp_path.replace(self.session_path)

    def _update(self, updater: Callable[[Dict[str, Any]], None]) -> None:
        data = self.load()
        updater(data)
        self.save(data)

    def update_state(self, state_data: Dict[str, Any]) -> None:
        self._update(lambda data: data.update(state_data))

    def enqueue_pending_score(self, score_entry: Dict[str, Any]) -> None:
        def updater(data: Dict[str, Any]) -> None:
            pending: List[Dict[str, Any]] = list(data.get("pending_scores", []))
            pending.append(score_entry)
            data["pending_scores"] = pending

        self._update(updater)

    def set_pending_scores(self, pending_scores: List[Dict[str, Any]]) -> None:
        self._update(lambda data: data.__setitem__("pending_scores", pending_scores))

    def get_pending_scores(self) -> List[Dict[str, Any]]:
        data = self.load()
        pending = data.get("pending_scores", [])
        return pending if isinstance(pending, list) else []

    def append_local_history(self, score_entry: Dict[str, Any]) -> None:
        def updater(data: Dict[str, Any]) -> None:
            history: List[Dict[str, Any]] = list(data.get("local_history", []))
            history.append(score_entry)
            data["local_history"] = history[-500:]

        self._update(updater)

    def get_local_history(self, player_name: str) -> List[Dict[str, Any]]:
        data = self.load()
        history = data.get("local_history", [])
        if not isinstance(history, list):
            return []
        lower_name = player_name.strip().lower()
        result: List[Dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).strip().lower() != lower_name:
                continue
            result.append(
                {
                    "score": int(item.get("score", 0)),
                    "date": str(item.get("date", "")),
                    "mode": str(item.get("mode", "")),
                    "lines": int(item.get("lines", 0)),
                }
            )
        return result

    def set_cached_leaderboard(self, leaderboard: List[Dict[str, Any]]) -> None:
        self._update(lambda data: data.__setitem__("cached_leaderboard", leaderboard))

    def get_cached_leaderboard(self) -> List[Dict[str, Any]]:
        data = self.load()
        value = data.get("cached_leaderboard", [])
        return value if isinstance(value, list) else []

    def set_cached_history(self, player_name: str, history: List[Dict[str, Any]]) -> None:
        def updater(data: Dict[str, Any]) -> None:
            cached = data.get("cached_history_by_name")
            if not isinstance(cached, dict):
                cached = {}
            cached[player_name] = history
            data["cached_history_by_name"] = cached

        self._update(updater)

    def get_cached_history(self, player_name: str) -> List[Dict[str, Any]]:
        data = self.load()
        cached = data.get("cached_history_by_name", {})
        if not isinstance(cached, dict):
            return []
        value = cached.get(player_name, [])
        return value if isinstance(value, list) else []
