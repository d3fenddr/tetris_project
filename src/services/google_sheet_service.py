from __future__ import annotations

import csv
import time
from io import StringIO
from typing import Dict, List, Tuple

import requests

from src.config import NETWORK_BACKOFF_SECONDS, NETWORK_RETRIES, NETWORK_TIMEOUT_SECONDS
from src.utils.date_utils import sort_key_from_sheet_date


class GoogleSheetError(RuntimeError):
    pass


class GoogleSheetService:
    def __init__(
        self,
        csv_url: str,
        form_url: str,
        field_name: str,
        field_score: str,
        timeout_seconds: float = NETWORK_TIMEOUT_SECONDS,
        retries: int = NETWORK_RETRIES,
        backoff_seconds: float = NETWORK_BACKOFF_SECONDS,
    ) -> None:
        self.csv_url = csv_url
        self.form_url = form_url
        self.field_name = field_name
        self.field_score = field_score
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
        raise GoogleSheetError(f"Network request failed: {last_error}")

    @staticmethod
    def _parse_score(raw: str | int | None) -> int | None:
        if raw is None:
            return None
        try:
            score = int(str(raw).strip())
        except ValueError:
            return None
        if score < 0:
            return None
        return score

    def _read_csv_rows(self) -> List[Dict[str, str]]:
        response = self._request("GET", self.csv_url)
        response.encoding = "utf-8"
        reader = csv.DictReader(StringIO(response.text))
        rows: List[Dict[str, str]] = []
        for row in reader:
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def get_player_history(self, name: str) -> List[Dict[str, str | int]]:
        rows = self._read_csv_rows()
        lower_name = name.strip().lower()
        history: List[Dict[str, str | int]] = []
        for row in rows:
            row_name = (row.get("Player Name") or row.get("name") or "").strip()
            if not row_name or row_name.lower() != lower_name:
                continue
            parsed_score = self._parse_score(row.get("Score") or row.get("score"))
            if parsed_score is None:
                continue
            history.append(
                {
                    "score": parsed_score,
                    "date": (row.get("Date") or row.get("date") or "").strip(),
                }
            )
        history.sort(key=lambda item: sort_key_from_sheet_date(str(item["date"])), reverse=True)
        return history

    def get_leaderboard(self) -> List[Tuple[str, Tuple[int, str]]]:
        rows = self._read_csv_rows()
        best_by_name: Dict[str, Tuple[int, str]] = {}
        for row in rows:
            name = (row.get("Player Name") or row.get("name") or "").strip()
            if not name:
                continue
            score = self._parse_score(row.get("Score") or row.get("score"))
            if score is None:
                continue
            date = (row.get("Date") or row.get("date") or "").strip()
            prev = best_by_name.get(name)
            if prev is None or score > prev[0]:
                best_by_name[name] = (score, date)
            elif prev is not None and score == prev[0]:
                if sort_key_from_sheet_date(date) > sort_key_from_sheet_date(prev[1]):
                    best_by_name[name] = (score, date)
        return sorted(best_by_name.items(), key=lambda item: item[1][0], reverse=True)

    def submit_score(self, name: str, score: int) -> None:
        clean_name = name.strip()
        if not clean_name:
            raise GoogleSheetError("Player name is empty.")
        parsed_score = self._parse_score(score)
        if parsed_score is None:
            raise GoogleSheetError("Score is invalid.")
        payload = {self.field_name: clean_name, self.field_score: parsed_score}
        self._request("POST", self.form_url, data=payload)

