from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TELEGRAM_WEBAPP_URL = os.getenv("TELEGRAM_WEBAPP_URL") or os.getenv("MINI_APP_URL", "https://example.com")
VALID_MODES = {"peaceful", "easy", "normal", "hard"}
MODE_LABELS = {
    "peaceful": "Peaceful",
    "easy": "Easy",
    "normal": "Normal",
    "hard": "Hard",
}

logger = logging.getLogger(__name__)


async def _fetch_json(url: str) -> Any:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def _play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Play Tetris", web_app=WebAppInfo(url=TELEGRAM_WEBAPP_URL))]]
    )


def _is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in ("group", "supergroup"))


async def _command_is_for_this_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.message.text:
        return False
    command = update.message.text.split(maxsplit=1)[0]
    if "@" not in command:
        return True
    mentioned = command.split("@", 1)[1].lower()
    bot_username = context.bot_data.get("username")
    if not bot_username:
        me = await context.bot.get_me()
        bot_username = me.username or ""
        context.bot_data["username"] = bot_username
    return mentioned == str(bot_username).lower()


def _mode_from_args(args: list[str]) -> str | None:
    if not args:
        return None
    mode = args[0].strip().lower()
    if mode in VALID_MODES:
        return mode
    return "invalid"


def _leaderboard_url(chat_id: int | None, mode: str | None) -> str:
    if chat_id is not None:
        base = f"{BACKEND_URL.rstrip('/')}/scores/telegram/group/{chat_id}"
        params = {"limit": 10}
    else:
        base = f"{BACKEND_URL.rstrip('/')}/scores/leaderboard"
        params = {"season": 2, "limit": 10}
    if mode:
        params["mode"] = mode
    return f"{base}?{urlencode(params)}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _command_is_for_this_bot(update, context):
        return
    if _is_group_chat(update):
        text = "Open Tetris Mini App and compete with this group."
    else:
        text = "Play Tetris Mini App."
    await update.message.reply_text(
        text,
        reply_markup=_play_keyboard(),
    )


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _command_is_for_this_bot(update, context):
        return
    text = "Open Tetris Mini App and compete with this group." if _is_group_chat(update) else "Play Tetris Mini App."
    await update.message.reply_text(text, reply_markup=_play_keyboard())


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _command_is_for_this_bot(update, context):
        return
    mode = _mode_from_args(context.args)
    if mode == "invalid":
        await update.message.reply_text("Use /leaderboard, or /leaderboard peaceful|easy|normal|hard.")
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        url = _leaderboard_url(chat.id, mode)
    else:
        url = _leaderboard_url(None, mode)

    try:
        rows = await _fetch_json(url)
    except Exception:
        await update.message.reply_text("Leaderboard is unavailable right now.")
        return

    if not rows:
        label = MODE_LABELS.get(mode or "", "this group" if _is_group_chat(update) else "Season 2")
        await update.message.reply_text(f"No scores yet for {label}.")
        return

    title = "Group leaderboard" if _is_group_chat(update) else "Season 2 leaderboard"
    if mode:
        title = f"{title} - {MODE_LABELS[mode]}"
    lines = [title]
    for idx, row in enumerate(rows[:10], start=1):
        username = row.get("nickname") or row.get("username", "unknown")
        score = row.get("score", 0)
        row_mode = MODE_LABELS.get(str(row.get("mode", "")).lower(), str(row.get("mode", "")))
        row_lines = row.get("lines", 0)
        lines.append(f"{idx}. {username} - {score} ({row_mode}, {row_lines} lines)")
    await update.message.reply_text("\n".join(lines))


async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _command_is_for_this_bot(update, context):
        return
    await update.message.reply_text(
        "Open the Mini App and link your account first. "
        "Then your personal stats will appear in the app profile screen."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _command_is_for_this_bot(update, context):
        return
    await update.message.reply_text(
        "/start - welcome and launch button\n"
        "/play - open Tetris Mini App\n"
        "/leaderboard [mode] - global or group leaderboard\n"
        "/my_stats - personal stats guidance\n"
        "/help - show commands\n"
        "Modes: peaceful, easy, normal, hard"
    )


async def post_init(application: Application) -> None:
    me = await application.bot.get_me()
    application.bot_data["username"] = me.username or ""
    logger.info("Bot username: @%s", me.username or "unknown")
    logger.info("Polling started.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info("Telegram token configured: %s", "yes" if BOT_TOKEN else "no")
    logger.info("WebApp URL: %s", TELEGRAM_WEBAPP_URL)
    logger.info("Backend URL: %s", BACKEND_URL)
    logger.warning("Polling is for local development only. Delete the Telegram webhook before polling with this token.")
    if "example.com" in TELEGRAM_WEBAPP_URL:
        logger.warning("TELEGRAM_WEBAPP_URL is still using an example URL.")
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("my_stats", my_stats))
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling()


if __name__ == "__main__":
    main()
