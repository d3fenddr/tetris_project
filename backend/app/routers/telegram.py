from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import User
from backend.app.schemas import (
    TelegramInitDataRequest,
    TelegramLinkResponse,
    TelegramValidationResponse,
)

router = APIRouter(prefix="/telegram", tags=["telegram"])


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


def _extract_telegram_user(data: dict[str, str]) -> tuple[int | None, str | None]:
    raw_user = data.get("user")
    if not raw_user:
        return None, None
    try:
        parsed = json.loads(raw_user)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(parsed, dict):
        return None, None
    user_id = parsed.get("id")
    username = parsed.get("username")
    if isinstance(user_id, int):
        return user_id, str(username) if username else None
    return None, None


@router.post("/validate-init-data", response_model=TelegramValidationResponse)
def validate_init_data(payload: TelegramInitDataRequest) -> TelegramValidationResponse:
    valid, data, error = _validate_init_data(payload.init_data)
    if not valid:
        return TelegramValidationResponse(valid=False, message=error)

    user_id, username = _extract_telegram_user(data)
    auth_date = int(data.get("auth_date", 0)) if data.get("auth_date") else None
    return TelegramValidationResponse(
        valid=True,
        telegram_user_id=user_id,
        username=username,
        auth_date=auth_date,
        message="initData is valid.",
    )


@router.post("/link-account", response_model=TelegramLinkResponse)
def link_account(
    payload: TelegramInitDataRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TelegramLinkResponse:
    valid, data, error = _validate_init_data(payload.init_data)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    telegram_user_id, _ = _extract_telegram_user(data)
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

