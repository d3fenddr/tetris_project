from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from typing import Any
from datetime import datetime, timedelta
from urllib.parse import parse_qsl

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.db_resilience import run_db_operation_with_retry
from backend.app.dependencies import get_current_user
from backend.app.models import RefreshSession, Score, User
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
VALID_BOT_COMMANDS = {"start", "play", "leaderboard", "my_stats", "help"}
VALID_GAME_MODES = {"peaceful", "easy", "normal", "hard"}
MODE_LABELS = {
    "peaceful": "Peaceful",
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}
logger = logging.getLogger(__name__)
_BOT_USERNAME: str | None = None


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


def _telegram_api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"


async def _get_bot_username() -> str:
    global _BOT_USERNAME
    if _BOT_USERNAME:
        return _BOT_USERNAME
    if not settings.telegram_bot_token:
        return ""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(_telegram_api_url("getMe"))
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("Telegram getMe failed: %s", exc.__class__.__name__)
        return ""
    result = payload.get("result") if isinstance(payload, dict) else {}
    username = result.get("username") if isinstance(result, dict) else ""
    _BOT_USERNAME = str(username or "")
    return _BOT_USERNAME


def _message_from_update(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    return message if isinstance(message, dict) else None


def _parse_command(text: str) -> tuple[str, str | None, list[str]] | None:
    if not text.startswith("/"):
        return None
    first, *rest = text.strip().split()
    command_part = first[1:]
    if not command_part:
        return None
    if "@" in command_part:
        command, mention = command_part.split("@", 1)
    else:
        command, mention = command_part, None
    return command.lower(), mention.lower() if mention else None, rest


async def _command_is_for_this_bot(mention: str | None) -> bool:
    if not mention:
        return True
    username = await _get_bot_username()
    if not username:
        return False
    return mention == username.lower()


def _chat_id_and_type(message: dict[str, Any]) -> tuple[int | None, str]:
    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None, ""
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return None, str(chat.get("type") or "")
    return chat_id, str(chat.get("type") or "")


def _webapp_keyboard(is_group: bool = False) -> dict[str, Any] | None:
    webapp_url = settings.telegram_webapp_url
    if not webapp_url or "example.com" in webapp_url:
        logger.warning("Telegram WebApp URL is not configured for production.")
        return None
    button: dict[str, Any] = {"text": "Play Tetris"}
    if is_group:
        button["url"] = webapp_url
    else:
        button["web_app"] = {"url": webapp_url}
    return {
        "inline_keyboard": [
            [button]
        ]
    }


async def _send_message(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token is not configured; message was not sent.")
        return
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(_telegram_api_url("sendMessage"), json=payload)
        if response.is_success:
            logger.info("Telegram sendMessage succeeded: status=%s chat_id=%s", response.status_code, chat_id)
            return
        logger.warning(
            "Telegram sendMessage failed: status=%s body=%s",
            response.status_code,
            response.text[:500],
        )
    except httpx.RequestError as exc:
        logger.warning("Telegram sendMessage request failed: %s", exc.__class__.__name__)


def _clean_mode(args: list[str]) -> str | None:
    if not args:
        return None
    mode = args[0].strip().lower()
    return mode if mode in VALID_GAME_MODES else "invalid"


def _leaderboard_rows(db: Session, chat_id: int | None, mode: str | None, limit: int = 10) -> list[Score]:
    clean_mode = mode or "all"
    query = db.query(Score).filter(Score.season == settings.current_season)
    if chat_id is not None:
        query = query.filter(Score.telegram_chat_id == chat_id)
    if clean_mode != "all":
        query = query.filter(Score.mode == clean_mode)

    candidate_rows = (
        query.order_by(Score.score.desc(), Score.created_at.asc(), Score.id.asc())
        .all()
    )
    best_rows: list[Score] = []
    seen_keys: set[tuple[int, str]] = set()
    for row in candidate_rows:
        key = (row.user_id, row.mode)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        best_rows.append(row)
        if len(best_rows) >= limit:
            break
    return best_rows


def _format_leaderboard(rows: list[Score], mode: str | None, is_group: bool) -> str:
    if not rows:
        return "No scores yet."
    title = "Group leaderboard" if is_group else f"Season {settings.current_season} leaderboard"
    if mode:
        title = f"{title} - {MODE_LABELS[mode]}"
    lines = [title]
    for idx, row in enumerate(rows, start=1):
        nickname = _display_bot_nickname(row.nickname_at_submission or row.user.nickname)
        mode_label = MODE_LABELS.get(row.mode, row.mode.title())
        lines.append(f"{idx}. {nickname} - {row.score} ({mode_label}, {row.lines} lines)")
    return "\n".join(lines)


def _display_bot_nickname(value: str | None) -> str:
    clean = (value or "").strip().lstrip("@")
    return clean or "unknown"


async def _handle_bot_command(
    command: str,
    args: list[str],
    chat_id: int,
    chat_type: str,
    db: Session,
) -> None:
    is_group = chat_type in {"group", "supergroup"}
    if command in {"start", "play"}:
        if is_group:
            text = "Open Tetris Mini App and compete with this group."
        else:
            text = "Welcome to Tetris. Open the Mini App to play."
        await _send_message(chat_id, text, _webapp_keyboard(is_group))
        return

    if command == "leaderboard":
        mode = _clean_mode(args)
        if mode == "invalid":
            await _send_message(chat_id, "Use /leaderboard, or /leaderboard peaceful|easy|normal|hard.")
            return
        group_chat_id = chat_id if is_group else None
        rows = _leaderboard_rows(db, group_chat_id, mode)
        await _send_message(chat_id, _format_leaderboard(rows, mode, is_group))
        return

    if command == "my_stats":
        await _send_message(
            chat_id,
            "Open the Mini App and link your account first. Then your personal stats will appear in the app profile screen.",
        )
        return

    if command == "help":
        await _send_message(
            chat_id,
            "/start - launch button\n"
            "/play - open Tetris Mini App\n"
            "/leaderboard [mode] - global or group leaderboard\n"
            "/my_stats - personal stats guidance\n"
            "/help - show commands\n"
            "Modes: peaceful, easy, normal, hard",
        )


@router.post("/bot/webhook/{secret}")
async def telegram_bot_webhook(
    secret: str,
    update: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    configured_secret = settings.telegram_webhook_secret
    if not configured_secret or not hmac.compare_digest(secret, configured_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret.")

    message = _message_from_update(update)
    if not message:
        return {"ok": True}
    text = message.get("text")
    if not isinstance(text, str):
        return {"ok": True}
    parsed = _parse_command(text)
    if not parsed:
        return {"ok": True}

    command, mention, args = parsed
    if command not in VALID_BOT_COMMANDS:
        return {"ok": True}
    if not await _command_is_for_this_bot(mention):
        return {"ok": True}

    chat_id, chat_type = _chat_id_and_type(message)
    if chat_id is None:
        return {"ok": True}

    try:
        await _handle_bot_command(command, args, chat_id, chat_type, db)
    except Exception as exc:
        logger.warning("Telegram webhook command failed: %s", exc.__class__.__name__)
        await _send_message(chat_id, "Bot command failed. Please try again later.")
    return {"ok": True}


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
