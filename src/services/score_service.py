from __future__ import annotations

from typing import Dict, List, Tuple

from src.services.google_sheet_service import GoogleSheetError, GoogleSheetService
from src.services.session_service import SessionService
from src.utils.date_utils import current_sheet_datetime, sort_key_from_sheet_date


class ScoreService:
    def __init__(self, google_service: GoogleSheetService, session_service: SessionService) -> None:
        self.google_service = google_service
        self.session_service = session_service

    def _normalize_leaderboard_cache(
        self,
        leaderboard: List[Tuple[str, Tuple[int, str]]],
    ) -> List[Dict[str, str | int]]:
        return [{"name": name, "score": score, "date": date} for name, (score, date) in leaderboard]

    @staticmethod
    def _denormalize_leaderboard_cache(
        cached: List[Dict[str, str | int]],
    ) -> List[Tuple[str, Tuple[int, str]]]:
        result: List[Tuple[str, Tuple[int, str]]] = []
        for item in cached:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                continue
            date = str(item.get("date", ""))
            result.append((name, (score, date)))
        return sorted(result, key=lambda x: x[1][0], reverse=True)

    def _merge_with_local_history(self, player_name: str, remote: List[Dict[str, str | int]]) -> List[Dict[str, str | int]]:
        local = self.session_service.get_local_history(player_name)
        combined = list(remote)
        combined.extend(local)
        # Keep a compact de-duplicated list by score+date.
        unique: Dict[tuple[int, str], Dict[str, str | int]] = {}
        for item in combined:
            key = (int(item.get("score", 0)), str(item.get("date", "")))
            unique[key] = {"score": key[0], "date": key[1]}
        result = list(unique.values())
        result.sort(key=lambda row: sort_key_from_sheet_date(str(row["date"])), reverse=True)
        return result

    def record_score(self, player_name: str, score: int) -> bool:
        clean_name = player_name.strip()
        if not clean_name or score < 0:
            return False

        local_entry = {
            "name": clean_name,
            "score": score,
            "date": current_sheet_datetime(),
        }
        self.session_service.append_local_history(local_entry)

        try:
            self.google_service.submit_score(clean_name, score)
            self.flush_pending_scores()
            return True
        except GoogleSheetError:
            self.session_service.enqueue_pending_score(local_entry)
            return False

    def flush_pending_scores(self) -> None:
        pending = self.session_service.get_pending_scores()
        if not pending:
            return

        still_pending: List[Dict[str, str | int]] = []
        for item in pending:
            name = str(item.get("name", "")).strip()
            try:
                score = int(item.get("score", 0))
            except (TypeError, ValueError):
                continue
            if not name or score < 0:
                continue
            try:
                self.google_service.submit_score(name, score)
            except GoogleSheetError:
                still_pending.append(item)
        self.session_service.set_pending_scores(still_pending)

    def get_player_history(self, player_name: str) -> List[Dict[str, str | int]]:
        clean_name = player_name.strip()
        if not clean_name:
            return []
        self.flush_pending_scores()
        try:
            history = self.google_service.get_player_history(clean_name)
            merged = self._merge_with_local_history(clean_name, history)
            self.session_service.set_cached_history(clean_name, merged)
            return merged
        except GoogleSheetError:
            cached = self.session_service.get_cached_history(clean_name)
            if cached:
                return cached
            return self.session_service.get_local_history(clean_name)

    def get_leaderboard(self) -> List[Tuple[str, Tuple[int, str]]]:
        self.flush_pending_scores()
        try:
            leaderboard = self.google_service.get_leaderboard()
            self.session_service.set_cached_leaderboard(self._normalize_leaderboard_cache(leaderboard))
            return leaderboard
        except GoogleSheetError:
            cached = self.session_service.get_cached_leaderboard()
            return self._denormalize_leaderboard_cache(cached)

