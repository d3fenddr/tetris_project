from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from src.config import CURRENT_SEASON, DEBUG_ONLINE_SCORE_FLOW
from src.services.backend_client import BackendClient, BackendClientError
from src.services.google_sheet_service import GoogleSheetError, GoogleSheetService
from src.services.session_service import SessionService
from src.utils.date_utils import current_sheet_datetime


@dataclass
class ScoreSubmissionResult:
    submitted: bool
    message: str
    score_id: int | None = None
    error: str = ""


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
        if self.backend_client.access_token:
            if DEBUG_ONLINE_SCORE_FLOW:
                print("[score-flow] Score token source: memory")
            return self.backend_client.access_token
        raw = self.session_service.load().get("account")
        if not isinstance(raw, dict):
            if DEBUG_ONLINE_SCORE_FLOW:
                print("[score-flow] Score token source: none")
            return None
        token = raw.get("access_token")
        if token:
            if DEBUG_ONLINE_SCORE_FLOW:
                print("[score-flow] Score token source: session")
            return str(token)
        if DEBUG_ONLINE_SCORE_FLOW:
            print("[score-flow] Score token source: none")
        return None

    def _require_backend_auth(self) -> None:
        token = self._load_access_token()
        if not token:
            raise BackendClientError("not logged in.")
        self.backend_client.set_access_token(token)

    def record_score(self, player_name: str, score: int, mode: str = "normal", lines: int = 0, level: int = 1) -> bool:
        return self.record_score_result(player_name, score, mode=mode, lines=lines, level=level).submitted

    def record_score_result(
        self,
        player_name: str,
        score: int,
        mode: str = "normal",
        lines: int = 0,
        level: int = 1,
    ) -> ScoreSubmissionResult:
        clean_name = player_name.strip()
        if not clean_name or score < 0:
            message = "Score was not submitted: missing player name or invalid score."
            if DEBUG_ONLINE_SCORE_FLOW:
                print(f"[score-flow] {message} name_present={bool(clean_name)} score={score}")
            return ScoreSubmissionResult(False, message, error=message)

        if DEBUG_ONLINE_SCORE_FLOW:
            raw_account = self.session_service.load().get("account")
            user_id = raw_account.get("user_id") if isinstance(raw_account, dict) else None
            username = raw_account.get("username") if isinstance(raw_account, dict) else ""
            print(
                "[score-flow] Recording game over score: "
                f"player={clean_name}, account={username or 'missing'}, user_id={user_id}, "
                f"score={score}, mode={mode}, lines={lines}, level={level}"
            )

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
            result = self.backend_client.submit_score(score=score, mode=mode, lines=lines, level=level)
            score_id = int(result["id"]) if isinstance(result, dict) and result.get("id") is not None else None
            message = "Score submitted to Season 2."
            if DEBUG_ONLINE_SCORE_FLOW:
                print(f"[score-flow] {message} score_id={score_id}")
            return ScoreSubmissionResult(True, message, score_id=score_id)
        except BackendClientError as exc:
            error = str(exc)
            message = f"Score was not submitted: {error}"
            if DEBUG_ONLINE_SCORE_FLOW:
                print(f"[score-flow] {message}")
            return ScoreSubmissionResult(False, message, error=error)

    def get_player_history(self, player_name: str = "") -> List[Dict[str, Any]]:
        try:
            self._require_backend_auth()
            return self.backend_client.get_my_history(season=CURRENT_SEASON, limit=50)
        except BackendClientError:
            return self.session_service.get_local_history(player_name)

    def get_leaderboard(self, mode: str | None = None) -> List[Dict[str, Any]]:
        try:
            return self.backend_client.get_leaderboard(season=CURRENT_SEASON, limit=10, mode=mode)
        except BackendClientError as exc:
            raise RuntimeError("Online leaderboard is unavailable.") from exc

    def get_season1_top3(self) -> List[Tuple[str, Tuple[int, str]]]:
        try:
            return self.google_service.get_leaderboard()[:3]
        except GoogleSheetError as exc:
            raise RuntimeError("Season 1 leaderboard is unavailable right now.") from exc
