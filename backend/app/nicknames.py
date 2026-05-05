from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import User


NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
NICKNAME_MIN_LENGTH = 3
NICKNAME_MAX_LENGTH = 20


def normalize_nickname(nickname: str) -> str:
    return nickname.strip().casefold()


def validate_nickname_format(nickname: str) -> str:
    clean = nickname.strip()
    if len(clean) < NICKNAME_MIN_LENGTH:
        raise ValueError(f"Nickname must be at least {NICKNAME_MIN_LENGTH} characters.")
    if len(clean) > NICKNAME_MAX_LENGTH:
        raise ValueError(f"Nickname must be at most {NICKNAME_MAX_LENGTH} characters.")
    if not NICKNAME_PATTERN.fullmatch(clean):
        raise ValueError("Nickname can contain only letters, numbers, and underscore.")
    return clean


def find_similar_nickname(
    db: Session,
    normalized_nickname: str,
    exclude_user_id: int | None = None,
) -> str | None:
    query = db.query(User)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)

    for user in query.all():
        existing = user.normalized_nickname or normalize_nickname(user.nickname)
        if existing == normalized_nickname:
            return user.nickname
        ratio = SequenceMatcher(None, existing, normalized_nickname).ratio()
        if ratio >= settings.similar_nickname_threshold:
            return user.nickname
    return None


def validate_available_nickname(
    db: Session,
    nickname: str,
    exclude_user_id: int | None = None,
) -> tuple[str, str]:
    clean = validate_nickname_format(nickname)
    normalized = normalize_nickname(clean)

    duplicate = (
        db.query(User)
        .filter(User.normalized_nickname == normalized)
        .filter(User.id != exclude_user_id if exclude_user_id is not None else True)
        .first()
    )
    if duplicate:
        raise ValueError("Nickname is already taken.")

    similar = find_similar_nickname(db, normalized, exclude_user_id=exclude_user_id)
    if similar:
        raise ValueError(f"Nickname is too similar to existing nickname '{similar}'.")

    return clean, normalized
