from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import requests

from src.config import (
    AUTH_NETWORK_TIMEOUT_SECONDS,
    CURRENT_SEASON,
    DEBUG_ONLINE_SCORE_FLOW,
    NETWORK_TIMEOUT_SECONDS,
    NETWORK_BACKOFF_SECONDS,
    NETWORK_RETRIES,
    SCORE_NETWORK_TIMEOUT_SECONDS,
    TETRIS_BACKEND_URL,
)


class BackendClientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, error_type: str = "backend") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type

    @property
    def is_unavailable(self) -> bool:
        return self.error_type == "network"


def _validation_error_message(detail: Any) -> str | None:
    if not isinstance(detail, list):
        return None
    for item in detail:
        if not isinstance(item, dict):
            continue
        location = item.get("loc")
        error_type = str(item.get("type", ""))
        if isinstance(location, list) and "password" in location and error_type == "string_too_short":
            ctx = item.get("ctx") if isinstance(item.get("ctx"), dict) else {}
            try:
                min_length = int(ctx.get("min_length", 6))
            except (TypeError, ValueError):
                min_length = 6
            return f"Password must be at least {min_length} characters."
        if isinstance(location, list) and "nickname" in location and error_type == "string_too_short":
            return "Nickname must be at least 3 characters."
    return None


def _friendly_error_message(path: str, status_code: int, detail: Any) -> str:
    validation_message = _validation_error_message(detail)
    if validation_message:
        return validation_message

    if path.startswith("/auth"):
        clean_detail = str(detail or "").strip()
        lowered = clean_detail.lower()
        if status_code == 401 or "wrong" in lowered or "invalid" in lowered:
            return "Nickname or password is incorrect."
        if status_code == 404 or "not found" in lowered:
            return "Account was not found."
        if status_code == 409 or "already" in lowered or "taken" in lowered:
            return "This nickname is already taken."
        if status_code >= 500:
            return "Account service is temporarily unavailable."
        return "Something went wrong. Please try again."

    return str(detail or "Backend request failed.")


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
        self._token_refresh_callback: Optional[Callable[[], Tuple[str, str]]] = None
        if DEBUG_ONLINE_SCORE_FLOW:
            print(f"[score-flow] Backend URL: {self.base_url}")

    def set_access_token(self, access_token: Optional[str]) -> None:
        self.access_token = access_token or None

    def set_token_refresh_callback(
        self, callback: Optional[Callable[[], Tuple[str, str]]]
    ) -> None:
        self._token_refresh_callback = callback

    def _headers(self) -> Dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, path: str, _allow_token_refresh: bool = True, **kwargs: Any) -> Any:
        should_log = DEBUG_ONLINE_SCORE_FLOW and (
            path.startswith("/scores")
            or path.startswith("/auth/me")
            or path.startswith("/auth/login")
            or path.startswith("/auth/register")
            or path.startswith("/auth/enter")
        )
        timeout = kwargs.pop("timeout", self._timeout_for_path(path))
        headers = kwargs.pop("headers", {})
        last_network_error: requests.RequestException | None = None
        for attempt in range(NETWORK_RETRIES + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=f"{self.base_url}{path}",
                    timeout=timeout,
                    headers={**self._headers(), **headers},
                    **kwargs,
                )
            except requests.Timeout as exc:
                last_network_error = exc
                message = "Online backend timed out."
            except requests.ConnectionError as exc:
                last_network_error = exc
                message = "Online backend is unavailable."
                self.session.close()
                self.session = requests.Session()
            except requests.RequestException as exc:
                last_network_error = exc
                message = "Online backend is unavailable."
            else:
                if response.status_code >= 500 and attempt < NETWORK_RETRIES:
                    if should_log:
                        print(f"[score-flow] {method} {path} HTTP {response.status_code}, retry {attempt + 1}/{NETWORK_RETRIES}")
                    time.sleep(NETWORK_BACKOFF_SECONDS * (attempt + 1))
                    continue
                break

            if should_log:
                print(
                    f"[score-flow] {method} {path} failed: "
                    f"{last_network_error.__class__.__name__ if last_network_error else 'RequestException'}, "
                    f"retry={attempt}/{NETWORK_RETRIES}, timeout={timeout}s"
                )
            if attempt < NETWORK_RETRIES:
                time.sleep(NETWORK_BACKOFF_SECONDS * (attempt + 1))
                continue
            raise BackendClientError(message, error_type="network") from last_network_error

        if should_log:
            print(f"[score-flow] {method} {path} -> HTTP {response.status_code}, timeout={timeout}s")

        if response.status_code == 401 and _allow_token_refresh and self._token_refresh_callback:
            if should_log:
                print(f"[score-flow] {method} {path} HTTP 401, attempting token refresh")
            try:
                new_access, _new_refresh = self._token_refresh_callback()
            except Exception:
                new_access = None
            if new_access:
                if should_log:
                    print(f"[score-flow] {method} {path} token refresh succeeded, retrying request")
                return self._request(method, path, _allow_token_refresh=False, **kwargs)
            if should_log:
                print(f"[score-flow] {method} {path} token refresh failed, propagating 401")

        if response.status_code >= 400:
            try:
                error_json = response.json()
                detail = error_json.get("detail") if isinstance(error_json, dict) else None
                if should_log and isinstance(error_json, dict):
                    print(f"[score-flow] {method} {path} error body keys: {sorted(error_json.keys())}")
            except ValueError as exc:
                detail = response.text
                if should_log:
                    print(f"[score-flow] {method} {path} error JSON parse failed: {exc.__class__.__name__}")
            message = _friendly_error_message(path, response.status_code, detail)
            if should_log:
                print(f"[score-flow] {method} {path} error: {str(detail or message)[:160]}")
            raise BackendClientError(message, status_code=response.status_code, error_type="http")

        if response.status_code == 204:
            return None
        try:
            data = response.json()
            if should_log:
                keys = sorted(data.keys()) if isinstance(data, dict) else []
                print(f"[score-flow] {method} {path} JSON parsed: yes, keys={keys}")
            return data
        except ValueError as exc:
            if should_log:
                print(f"[score-flow] {method} {path} JSON parsed: no, error={exc.__class__.__name__}")
            return None

    def _timeout_for_path(self, path: str) -> float:
        if path.startswith(("/auth/register", "/auth/login", "/auth/enter", "/auth/me")):
            return AUTH_NETWORK_TIMEOUT_SECONDS
        if path.startswith("/scores"):
            return SCORE_NETWORK_TIMEOUT_SECONDS
        return self.timeout_seconds

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

    def refresh_session(self, refresh_token: str) -> BackendAuth:
        data = self._request(
            "POST",
            "/auth/refresh",
            _allow_token_refresh=False,
            json={"refresh_token": refresh_token},
        )
        auth = self._auth_from_response(data, default_created=False)
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
        try:
            result = self._request(
                "POST",
                "/scores",
                json=payload,
            )
        except BackendClientError as exc:
            if exc.status_code == 409:
                if DEBUG_ONLINE_SCORE_FLOW:
                    print("[score-flow] Score submit duplicate acknowledged as already saved.")
                return {"id": None, "duplicate": True}
            raise
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
