from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.config import CURRENT_SEASON
from src.services.backend_client import BackendClient, BackendClientError
from src.services.google_sheet_service import GoogleSheetError, GoogleSheetService
from src.services.session_service import SessionService
from src.utils.date_utils import current_sheet_datetime


class ScoreService:
    def __init__(
        self,
        google_service: GoogleSheetService,
        session_service: SessionService,
        backend_client: BackendClient,
    ) -> None:
        self.google_service = google_service
        self.session_service = session_service
        self.backend_client = backend_client

    def _load_access_token(self) -> str | None:
        raw = self.session_service.load().get("account")
        if not isinstance(raw, dict):
            return None
        token = raw.get("access_token")
        return str(token) if token else None

    def _require_backend_auth(self) -> None:
        token = self._load_access_token()
        if not token:
            raise BackendClientError("Log in to submit Season 2 scores.")
        self.backend_client.set_access_token(token)

    def record_score(self, player_name: str, score: int, mode: str = "normal", lines: int = 0, level: int = 1) -> bool:
        clean_name = player_name.strip()
        if not clean_name or score < 0:
            return False

        local_entry = {
            "name": clean_name,
            "score": score,
            "date": current_sheet_datetime(),
            "mode": mode,
            "lines": lines,
            "season": CURRENT_SEASON,
        }
        self.session_service.append_local_history(local_entry)

        try:
            self._require_backend_auth()
            self.backend_client.submit_score(score=score, mode=mode, lines=lines, level=level)
            return True
        except BackendClientError:
            return False

    def get_player_history(self, player_name: str = "") -> List[Dict[str, Any]]:
        try:
            self._require_backend_auth()
            return self.backend_client.get_my_history(season=CURRENT_SEASON, limit=50)
        except BackendClientError:
            return self.session_service.get_local_history(player_name)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        try:
            return self.backend_client.get_leaderboard(season=CURRENT_SEASON, limit=10)
        except BackendClientError as exc:
            raise RuntimeError("Online leaderboard is unavailable.") from exc

    def get_season1_top3(self) -> List[Tuple[str, Tuple[int, str]]]:
        try:
            return self.google_service.get_leaderboard()[:3]
        except GoogleSheetError as exc:
            raise RuntimeError("Season 1 leaderboard is unavailable right now.") from exc
