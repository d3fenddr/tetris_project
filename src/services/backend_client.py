from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from src.config import CURRENT_SEASON, NETWORK_TIMEOUT_SECONDS, TETRIS_BACKEND_URL


class BackendClientError(RuntimeError):
    pass


@dataclass
class BackendAuth:
    access_token: str
    refresh_token: str


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

    def set_access_token(self, access_token: Optional[str]) -> None:
        self.access_token = access_token or None

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
                headers={**self._headers(), **kwargs.pop("headers", {})},
                **kwargs,
            )
        except requests.RequestException as exc:
            raise BackendClientError("Online backend is unavailable.") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text
            raise BackendClientError(str(detail or "Backend request failed."))

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
        return self._request(
            "POST",
            "/scores",
            json={
                "score": score,
                "mode": mode,
                "lines": lines,
                "level": level,
                "season": season,
                "platform": "desktop",
                "client_game_id": str(uuid4()),
            },
        )

    def get_leaderboard(self, season: int = CURRENT_SEASON, limit: int = 10) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/scores/leaderboard?season={season}&limit={limit}")
        return data if isinstance(data, list) else []

    def get_my_history(self, season: int = CURRENT_SEASON, limit: int = 50) -> List[Dict[str, Any]]:
        data = self._request("GET", f"/scores/history/me?season={season}&limit={limit}")
        return data if isinstance(data, list) else []
