from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests

from src.config import CURRENT_SEASON, DEBUG_ONLINE_SCORE_FLOW, NETWORK_TIMEOUT_SECONDS, TETRIS_BACKEND_URL


class BackendClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, error_type: str = "backend") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type

    @property
    def is_unavailable(self) -> bool:
        return self.error_type == "network"


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
            path.startswith("/scores")
            or path.startswith("/auth/me")
            or path.startswith("/auth/login")
            or path.startswith("/auth/register")
            or path.startswith("/auth/enter")
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
            raise BackendClientError("Online backend is unavailable.", error_type="network") from exc

        if should_log:
            print(f"[score-flow] {method} {path} -> HTTP {response.status_code}")

        if response.status_code >= 400:
            try:
                error_json = response.json()
                detail = error_json.get("detail") if isinstance(error_json, dict) else None
                if should_log and isinstance(error_json, dict):
                    print(f"[score-flow] {method} {path} error body keys: {sorted(error_json.keys())}")
            except ValueError:
                detail = response.text
            message = str(detail or "Backend request failed.")
            if should_log:
                print(f"[score-flow] {method} {path} error: {message[:160]}")
            raise BackendClientError(message, status_code=response.status_code, error_type="http")

        if response.status_code == 204:
            return None
        try:
            data = response.json()
            if should_log:
                keys = sorted(data.keys()) if isinstance(data, dict) else []
                print(f"[score-flow] {method} {path} JSON parsed: yes, keys={keys}")
            return data
        except ValueError:
            if should_log:
                print(f"[score-flow] {method} {path} JSON parsed: no")
            return None

    def register(self, nickname: str, password: str) -> BackendAuth:
        data = self._request("POST", "/auth/register", json={"nickname": nickname, "password": password})
        auth = self._auth_from_response(data, default_created=True)
        self.set_access_token(auth.access_token)
        return auth

    def login(self, nickname: str, password: str) -> BackendAuth:
        data = self._request("POST", "/auth/login", json={"nickname": nickname, "password": password})
        auth = self._auth_from_response(data, default_created=False)
        self.set_access_token(auth.access_token)
        return auth

    def authenticate_or_register(self, nickname: str, password: str) -> BackendAuth:
        data = self._request("POST", "/auth/enter", json={"nickname": nickname, "password": password})
        auth = self._auth_from_response(data, default_created=bool(data.get("created", False)) if isinstance(data, dict) else False)
        self.set_access_token(auth.access_token)
        return auth

    def _auth_from_response(self, data: Any, default_created: bool = False) -> BackendAuth:
        if not isinstance(data, dict):
            raise BackendClientError("Unexpected auth response from backend.", error_type="parse")
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        user = data.get("user") if isinstance(data.get("user"), dict) else None
        if not access_token or not refresh_token:
            raise BackendClientError("Backend auth response did not include tokens.", error_type="parse")
        if DEBUG_ONLINE_SCORE_FLOW:
            print(
                "[score-flow] Auth response parsed: "
                f"success=yes, access_token=yes, refresh_token=yes, user={'yes' if user else 'no'}, "
                f"user_id={user.get('id') if user else None}, nickname={user.get('nickname') if user else None}"
            )
        auth = BackendAuth(
            access_token=str(access_token),
            refresh_token=str(refresh_token),
            created=bool(data.get("created", default_created)),
            user=user,
        )
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
