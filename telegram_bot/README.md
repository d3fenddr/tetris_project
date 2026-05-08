# Telegram Bot (Scaffold)

## Env vars
- `TELEGRAM_BOT_TOKEN` (required)
- `BACKEND_URL` (default: `http://localhost:8000`)
- `TELEGRAM_WEBAPP_URL` (Mini App HTTPS URL)
- `MINI_APP_URL` (legacy fallback if `TELEGRAM_WEBAPP_URL` is not set)

## Run
```bash
pip install -r telegram_bot/requirements.txt
python telegram_bot/bot.py
```

## Commands
- `/start`
- `/play`
- `/leaderboard`
- `/my_stats`
- `/help`
