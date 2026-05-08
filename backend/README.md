# Tetris Backend (FastAPI)

## Features
- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PATCH /auth/me/nickname`
- Scores: `POST /scores`, `GET /scores/leaderboard?season=2`, `GET /scores/history/me?season=2`, `GET /scores/telegram/group/{chat_id}`
- Telegram: `POST /telegram/validate-init-data`, `POST /telegram/link-account`
- Utility: `GET /ping`, `GET /health`, `GET /version`

Accounts use nickname + password only. Nicknames are normalized case-insensitively, must be unique, and similar nicknames are blocked with a simple `difflib` similarity check.

Season 2 is the active database-backed leaderboard. Season 1 remains archived in the desktop client through the old Google leaderboard reader only.

## Env vars
- `TETRIS_DATABASE_URL=postgresql://...` (default: `sqlite:///./tetris.db`; `postgres://` is normalized automatically)
- `TETRIS_SECRET_KEY=change-me` (set a strong secret in production)
- `TETRIS_ACCESS_TOKEN_EXPIRE_MINUTES=2880`
- `TETRIS_REFRESH_TOKEN_EXPIRE_DAYS=30`
- `TETRIS_DB_KEEPALIVE_ENABLED=true`
- `TETRIS_DB_KEEPALIVE_INTERVAL_SECONDS=240`
- `TETRIS_CURRENT_SEASON` (default: `2`)
- `TETRIS_ARCHIVED_SEASON` (default: `1`)
- `TETRIS_SIMILAR_NICKNAME_THRESHOLD` (default: `0.85`)
- `TELEGRAM_BOT_TOKEN` (required for initData validation)
- `TELEGRAM_AUTH_MAX_AGE_SECONDS`

## Run
```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Health checks:
```bash
curl http://localhost:8000/ping
curl http://localhost:8000/health
```

`/ping` is fast and does not touch the database. `/health` runs `SELECT 1` and returns HTTP 503 with `{"status":"degraded","database":"unavailable"}` when the database is temporarily unavailable.

## Render and Neon free-tier notes

Recommended setup:
- Use an uptime monitor such as UptimeRobot, Better Stack, Cron-job.org, or a GitHub Actions schedule.
- Hit `https://YOUR_RENDER_SERVICE.onrender.com/ping` every 5 minutes to keep Render awake.
- Optionally hit `https://YOUR_RENDER_SERVICE.onrender.com/health` every 5 minutes when you also want to check or warm the database.

The backend DB keepalive loop only runs while the Render service itself is awake. Do not rely only on internal keepalive, because Render sleeping stops backend code entirely.
