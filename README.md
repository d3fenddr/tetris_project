# Tetris Project

This repository contains a pygame desktop Tetris game plus migration scaffolds for a FastAPI backend, Telegram bot, and React/TypeScript Telegram Mini App.

## Desktop App

- Entry point: `main.py`
- Modular source: `src/`
- Assets: `assets/`
- Season 2 accounts and leaderboard use the FastAPI backend.

Run desktop:
```bash
pip install -r requirements.txt
python main.py
```

## Backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Set `TETRIS_BACKEND_URL` for the desktop client if the backend is not on `http://127.0.0.1:8000`.

Backend production env vars:
```bash
TETRIS_DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME
TETRIS_SECRET_KEY=change-me
TETRIS_ACCESS_TOKEN_EXPIRE_MINUTES=2880
TETRIS_REFRESH_TOKEN_EXPIRE_DAYS=30
TETRIS_DB_KEEPALIVE_ENABLED=true
TETRIS_DB_KEEPALIVE_INTERVAL_SECONDS=240
```

For Render and Neon free tiers, configure an external uptime monitor to call `https://YOUR_RENDER_SERVICE.onrender.com/ping` every 5 minutes. Use `/health` instead if you also want the monitor to check and warm the database. The internal DB keepalive only runs while Render is awake, so it cannot prevent Render free tier sleeping by itself.

## Telegram Bot

Set `TELEGRAM_BOT_TOKEN` and related values from `.env.example`, then run:
```bash
pip install -r telegram_bot/requirements.txt
python telegram_bot/bot.py
```

## Web Mini App

```bash
cd webapp
npm install
npm run dev
```

Set `VITE_BACKEND_URL` for the Mini App frontend. When deploying the Telegram Mini App, host `webapp/dist/` over HTTPS, set the bot `TELEGRAM_WEBAPP_URL`, and add the frontend origin to backend `TETRIS_CORS_ORIGINS`.

The Mini App supports Telegram initData authentication through the backend, desktop keyboard controls, mobile swipe gestures, and on-screen hold controls for left/right/down movement.

## Asset Folders

- Images: `assets/images/`
- Music: `assets/audio/music/`
- Sound effects: `assets/audio/sounds/`

Place new desktop game images and audio inside these folders and reference them through project-relative `assets/...` paths.

## Notes

- Pygame desktop gameplay is preserved.
- Season 2 is the active backend/database leaderboard and starts empty.
- New desktop scores submit to the backend only when the player is logged in.
- Season 1 is archived: the desktop app can still show the old Google leaderboard top 3 as `Season 1 Top 3`.
- Use environment variables for all secrets/tokens. See `.env.example`.
- See `docs/PROJECT_STATE.md` for the current architecture and asset usage report.

## Season 2 Account Flow

1. Run the backend.
2. Run the desktop game.
3. Open `Profile` from the main menu.
4. Register or log in with nickname + password.
5. Play a game; logged-in scores submit to Season 2.
6. Open `Leaderboard` for Season 2 or `Season 1 Top 3` for archived winners.

## Release/update workflow

1. Update `APP_VERSION` in `src/version.py`.
2. Commit the version change.
3. Build the Windows exe with PyInstaller.
4. Create a GitHub Release with a matching tag, for example `v1.0.1`.
5. Upload the exe or zip to the release assets.
6. Users with older versions will see an update prompt on startup.

The current updater safely checks GitHub Releases and opens the release or asset download in the browser. It does not silently replace the running exe. Full silent replacement on Windows would require a separate updater executable.
