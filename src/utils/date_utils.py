from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.config import SHEET_DATETIME_FORMAT


def parse_sheet_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, SHEET_DATETIME_FORMAT)
    except (TypeError, ValueError):
        return None


def sort_key_from_sheet_date(value: str) -> datetime:
    parsed = parse_sheet_datetime(value)
    return parsed if parsed else datetime.min


def format_short_date(value: str) -> str:
    parsed = parse_sheet_datetime(value)
    if not parsed:
        return "??.??.??"
    return parsed.strftime("%d.%m.%y")


def format_short_time(value: str) -> str:
    parsed = parse_sheet_datetime(value)
    if not parsed:
        return "??:??"
    return parsed.strftime("%H:%M")


def current_sheet_datetime() -> str:
    return datetime.now().strftime(SHEET_DATETIME_FORMAT)

