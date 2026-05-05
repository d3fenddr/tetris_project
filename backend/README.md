# Tetris Backend (FastAPI)

## Features
- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `PATCH /auth/me/nickname`
- Scores: `POST /scores`, `GET /scores/leaderboard?season=2`, `GET /scores/history/me?season=2`, `GET /scores/telegram/group/{chat_id}`
- Telegram: `POST /telegram/validate-init-data`, `POST /telegram/link-account`
- Utility: `GET /health`, `GET /version`

Accounts use nickname + password only. Nicknames are normalized case-insensitively, must be unique, and similar nicknames are blocked with a simple `difflib` similarity check.

Season 2 is the active database-backed leaderboard. Season 1 remains archived in the desktop client through the old Google leaderboard reader only.

## Env vars
- `TETRIS_DATABASE_URL` (default: `sqlite:///./tetris.db`; PostgreSQL URLs are supported when backend requirements are installed)
- `TETRIS_SECRET_KEY` (set strong secret in production)
- `TETRIS_ACCESS_TOKEN_EXPIRE_MINUTES`
- `TETRIS_REFRESH_TOKEN_EXPIRE_DAYS`
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
