from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.db_resilience import run_db_operation_with_retry
from backend.app.dependencies import get_current_user
from backend.app.models import RefreshSession, User
from backend.app.schemas import (
    AuthResponse,
    TelegramInitDataRequest,
    TelegramLinkResponse,
    TelegramValidationResponse,
    TokenPairResponse,
    UserResponse,
)
from backend.app.security import create_access_token, create_refresh_token, hash_password, hash_refresh_token

router = APIRouter(prefix="/telegram", tags=["telegram"])
TELEGRAM_NICKNAME_PATTERN = re.compile(r"[^A-Za-z0-9_]+")


def _parse_init_data(init_data: str) -> dict[str, str]:
    return {key: value for key, value in parse_qsl(init_data, keep_blank_values=True)}


def _validate_init_data(init_data: str) -> tuple[bool, dict[str, str], str]:
    if not settings.telegram_bot_token:
        return False, {}, "TELEGRAM_BOT_TOKEN is not configured."

    data = _parse_init_data(init_data)
    received_hash = data.get("hash", "")
    if not received_hash:
        return False, data, "Missing hash in initData."

    data_check_pairs = []
    for key in sorted(data.keys()):
        if key == "hash":
            continue
        data_check_pairs.append(f"{key}={data[key]}")
    data_check_string = "\n".join(data_check_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=settings.telegram_bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return False, data, "Hash mismatch."

    auth_date_raw = data.get("auth_date")
    try:
        auth_date = int(auth_date_raw) if auth_date_raw is not None else 0
    except ValueError:
        return False, data, "Invalid auth_date."

    now = int(time.time())
    if now - auth_date > settings.telegram_auth_max_age_seconds:
        return False, data, "initData has expired."
    return True, data, ""


def _extract_telegram_user(data: dict[str, str]) -> tuple[int | None, str | None, str | None]:
    raw_user = data.get("user")
    if not raw_user:
        return None, None, None
    try:
        parsed = json.loads(raw_user)
    except json.JSONDecodeError:
        return None, None, None
    if not isinstance(parsed, dict):
        return None, None, None
    user_id = parsed.get("id")
    username = parsed.get("username")
    first_name = parsed.get("first_name")
    if isinstance(user_id, int):
        return user_id, str(username).lstrip("@") if username else None, str(first_name) if first_name else None
    return None, None, None


def _telegram_nickname(
    db: Session,
    telegram_user_id: int,
    username: str | None,
    first_name: str | None = None,
) -> tuple[str, str]:
    clean_username = TELEGRAM_NICKNAME_PATTERN.sub("_", (username or "").lstrip("@")).strip("_")
    clean_first_name = TELEGRAM_NICKNAME_PATTERN.sub("_", first_name or "").strip("_")
    candidates = []
    if len(clean_username) >= 3:
        candidates.append(clean_username[:20])
    if len(clean_first_name) >= 3:
        candidates.append(clean_first_name[:20])
    candidates.append(f"telegram_{telegram_user_id}"[:20])

    for candidate in candidates:
        normalized = candidate.casefold()
        existing = db.query(User).filter(User.normalized_nickname == normalized).first()
        if existing is None or existing.telegram_user_id == telegram_user_id:
            return candidate, normalized
    fallback = f"tg_{secrets.token_hex(4)}"
    return fallback, fallback.casefold()


def _token_pair_for_user(db: Session, user: User) -> TokenPairResponse:
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    access_token = create_access_token(subject=str(user.id), extra_claims={"nickname": user.nickname})
    refresh_token = create_refresh_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        nickname=user.nickname,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        games_played=user.games_played or 0,
        best_score=user.best_score or 0,
        current_season_rank=None,
    )


@router.post("/validate-init-data", response_model=TelegramValidationResponse)
def validate_init_data(payload: TelegramInitDataRequest) -> TelegramValidationResponse:
    valid, data, error = _validate_init_data(payload.init_data)
    if not valid:
        return TelegramValidationResponse(valid=False, message=error)

    user_id, username, _first_name = _extract_telegram_user(data)
    auth_date = int(data.get("auth_date", 0)) if data.get("auth_date") else None
    return TelegramValidationResponse(
        valid=True,
        telegram_user_id=user_id,
        username=username,
        auth_date=auth_date,
        message="initData is valid.",
    )


@router.post("/auth", response_model=AuthResponse)
def telegram_auth(payload: TelegramInitDataRequest, db: Session = Depends(get_db)) -> AuthResponse:
    def operation() -> AuthResponse:
        valid, data, error = _validate_init_data(payload.init_data)
        if not valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

        telegram_user_id, username, first_name = _extract_telegram_user(data)
        if telegram_user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram user data is missing.")

        user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
        created = False
        if user is None:
            nickname, normalized = _telegram_nickname(db, telegram_user_id, username, first_name)
            user = User(
                nickname=nickname,
                normalized_nickname=normalized,
                telegram_user_id=telegram_user_id,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            db.flush()
            created = True

        tokens = _token_pair_for_user(db, user)
        user_response = _user_response(user)
        db.commit()
        return AuthResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            created=created,
            user=user_response,
        )

    try:
        return run_db_operation_with_retry(db, "telegram/auth", operation)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Telegram account already exists.")


@router.post("/link-account", response_model=TelegramLinkResponse)
def link_account(
    payload: TelegramInitDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramLinkResponse:
    valid, data, error = _validate_init_data(payload.init_data)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    telegram_user_id, _, _ = _extract_telegram_user(data)
    if telegram_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram user data is missing in initData.",
        )

    existing = (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id, User.id != current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Telegram account already linked.")

    current_user.telegram_user_id = telegram_user_id
    db.commit()
    return TelegramLinkResponse(
        linked=True,
        telegram_user_id=telegram_user_id,
        message="Telegram account linked successfully.",
    )
