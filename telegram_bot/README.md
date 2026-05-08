# Telegram Bot

## Env vars
- `TELEGRAM_BOT_TOKEN` (required)
- `BACKEND_URL` (production: `https://tetris-project-ahgg.onrender.com`)
- `TELEGRAM_WEBAPP_URL` (Mini App HTTPS URL)
- `MINI_APP_URL` (legacy fallback if `TELEGRAM_WEBAPP_URL` is not set)
- `TELEGRAM_WEBHOOK_SECRET` (required for production webhook)

## Production webhook

Production uses the existing FastAPI backend instead of polling:

```text
POST https://tetris-project-ahgg.onrender.com/telegram/bot/webhook/<TELEGRAM_WEBHOOK_SECRET>
```

Deploy the backend with:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBAPP_URL=https://tetris-project-dun.vercel.app
MINI_APP_URL=https://tetris-project-dun.vercel.app
BACKEND_URL=https://tetris-project-ahgg.onrender.com
TELEGRAM_WEBHOOK_SECRET=random-long-secret
```

Then set the webhook:

```bash
python scripts/set_telegram_webhook.py
```

Or with curl:

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://tetris-project-ahgg.onrender.com/telegram/bot/webhook/<TELEGRAM_WEBHOOK_SECRET>"
```

Delete webhook:

```bash
python scripts/delete_telegram_webhook.py
```

Webhook and polling must not run at the same time for the same token.

## Local polling
```bash
pip install -r telegram_bot/requirements.txt
python telegram_bot/bot.py
```

Use local polling only for development. Delete the production webhook first if you use the same token.

## Commands
- `/start`
- `/play`
- `/leaderboard`
- `/leaderboard peaceful`
- `/leaderboard easy`
- `/leaderboard normal`
- `/leaderboard hard`
- `/my_stats`
- `/help`

In groups, Telegram may send commands as `/play@BotUsername` or `/leaderboard@BotUsername peaceful`.
The bot responds to commands addressed to itself and ignores commands addressed to other bots. If group
commands do not arrive, check the bot's BotFather privacy mode with `/setprivacy`.
