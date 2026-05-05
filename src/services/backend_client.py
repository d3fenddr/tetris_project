from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from src.config import CURRENT_SEASON, DEBUG_ONLINE_SCORE_FLOW, NETWORK_TIMEOUT_SECONDS, TETRIS_BACKEND_URL


class BackendClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class BackendAuth:
    access_token: str
    refresh_token: str
    created: bool = False
    user: Optional[Dict[str, Any]] = None


class BackendClient:
    def __init__(
        self,
        base_url: str = TETRIS_BACKEND_URL,
        timeout_seconds: float = NETWORK_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.access_token: Optional[str] = None
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Backend URL: {self.base_url}")

    def set_access_token(self, access_token: Optional[str]) -> None:
        self.access_token = access_token or None

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        should_log = DEBUG_ONLINE_SCORE_FLOW and (
            path.startswith("/scores") or path.startswith("/auth/me")
        )
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
                headers={**self._headers(), **kwargs.pop("headers", {})},
                **kwargs,
            )
        except requests.RequestException as exc:
            if should_log:
                print(f"[score-flow] {method} {path} failed: backend unavailable")
            raise BackendClientError("Online backend is unavailable.") from exc

        if should_log:
            print(f"[score-flow] {method} {path} -> HTTP {response.status_code}")

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text
            message = str(detail or "Backend request failed.")
            if should_log:
                print(f"[score-flow] {method} {path} error: {message[:160]}")
            raise BackendClientError(message, status_code=response.status_code)

        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def register(self, nickname: str, password: str) -> Dict[str, Any]:
        return self._request("POST", "/auth/register", json={"nickname": nickname, "password": password})

    def login(self, nickname: str, password: str) -> BackendAuth:
        data = self._request("POST", "/auth/login", json={"nickname": nickname, "password": password})
        auth = BackendAuth(access_token=str(data["access_token"]), refresh_token=str(data["refresh_token"]))
        self.set_access_token(auth.access_token)
        return auth

    def authenticate_or_register(self, nickname: str, password: str) -> BackendAuth:
        data = self._request("POST", "/auth/enter", json={"nickname": nickname, "password": password})
        auth = BackendAuth(
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]),
            created=bool(data.get("created", False)),
            user=data.get("user") if isinstance(data.get("user"), dict) else None,
        )
        self.set_access_token(auth.access_token)
        return auth

    def logout(self, refresh_token: str) -> None:
        self._request("POST", "/auth/logout", json={"refresh_token": refresh_token})

    def get_current_user(self) -> Dict[str, Any]:
        return self._request("GET", "/auth/me")

    def change_nickname(self, nickname: str) -> Dict[str, Any]:
        return self._request("PATCH", "/auth/me/nickname", json={"nickname": nickname})

    def submit_score(
        self,
        score: int,
        mode: str,
        lines: int = 0,
        level: int = 1,
        season: int = CURRENT_SEASON,
    ) -> Dict[str, Any]:
        payload = {
            "score": score,
            "mode": mode,
            "lines": lines,
            "level": level,
            "season": season,
            "platform": "desktop",
            "client_game_id": str(uuid4()),
        }
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Submit payload: {payload}")
            print(f"[score-flow] Auth token present: {bool(self.access_token)}")
        result = self._request(
            "POST",
            "/scores",
            json=payload,
        )
        if DEBUG_ONLINE_SCORE_FLOW:
            score_id = result.get("id") if isinstance(result, dict) else None
            print(f"[score-flow] Score submit succeeded: id={score_id}")
        return result

    def get_leaderboard(
        self,
        season: int = CURRENT_SEASON,
        limit: int = 10,
        mode: str | None = None,
    ) -> List[Dict[str, Any]]:
        query = f"/scores/leaderboard?season={season}&limit={limit}"
        if mode and mode != "all":
            query += f"&mode={mode}"
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Fetch leaderboard: season={season}, mode={mode or 'all'}, limit={limit}")
        data = self._request("GET", query)
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Leaderboard rows received: {len(data) if isinstance(data, list) else 0}")
        return data if isinstance(data, list) else []

    def get_my_history(self, season: int = CURRENT_SEASON, limit: int = 50) -> List[Dict[str, Any]]:
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Fetch history: season={season}, limit={limit}")
        data = self._request("GET", f"/scores/history/me?season={season}&limit={limit}")
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] History rows received: {len(data) if isinstance(data, list) else 0}")
        return data if isinstance(data, list) else []
