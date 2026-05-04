from __future__ import annotations

import os
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://example.com")


async def _fetch_json(url: str) -> Any:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def _play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Play Tetris", web_app=WebAppInfo(url=MINI_APP_URL))]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Welcome to Tetris.\nUse /play to launch the Mini App.",
        reply_markup=_play_keyboard(),
    )


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text("Launch game:", reply_markup=_play_keyboard())


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat = update.effective_chat
    if chat and chat.type in ("group", "supergroup"):
        url = f"{BACKEND_URL}/scores/telegram/group/{chat.id}"
    else:
        url = f"{BACKEND_URL}/scores/leaderboard"

    try:
        rows = await _fetch_json(url)
    except Exception:
        await update.message.reply_text("Leaderboard is unavailable right now.")
        return

    if not rows:
        await update.message.reply_text("No scores yet.")
        return

    lines = []
    for idx, row in enumerate(rows[:10], start=1):
        username = row.get("username", "unknown")
        score = row.get("score", 0)
        lines.append(f"{idx}. {username} - {score}")
    await update.message.reply_text("\n".join(lines))


async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Open the Mini App and link your account first. "
        "Then your personal stats will appear in the app profile screen."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "/start - welcome and launch button\n"
        "/play - open Tetris Mini App\n"
        "/leaderboard - global or group leaderboard\n"
        "/my_stats - personal stats guidance\n"
        "/help - show commands"
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("my_stats", my_stats))
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling()


if __name__ == "__main__":
    main()

