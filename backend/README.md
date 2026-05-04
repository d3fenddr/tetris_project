# Tetris Backend (FastAPI)

## Features
- Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- Scores: `POST /scores`, `GET /scores/leaderboard`, `GET /scores/history/me`, `GET /scores/telegram/group/{chat_id}`
- Telegram: `POST /telegram/validate-init-data`, `POST /telegram/link-account`
- Utility: `GET /health`, `GET /version`

## Env vars
- `TETRIS_DATABASE_URL` (default: `sqlite:///./tetris.db`)
- `TETRIS_SECRET_KEY` (set strong secret in production)
- `TETRIS_ACCESS_TOKEN_EXPIRE_MINUTES`
- `TETRIS_REFRESH_TOKEN_EXPIRE_DAYS`
- `TELEGRAM_BOT_TOKEN` (required for initData validation)
- `TELEGRAM_AUTH_MAX_AGE_SECONDS`

## Run
```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

