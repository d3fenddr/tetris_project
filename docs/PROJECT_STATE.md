# Project State

## Overview

This project is a Tetris repository with a working pygame desktop client and migration scaffolds for a backend API, Telegram bot, and Telegram Mini App web frontend. The desktop client is currently the most complete game implementation. The backend, bot, and webapp provide the foundation for account, score, Telegram, and Mini App workflows.

## Current Architecture

### Desktop Game

The desktop game is implemented in Python with pygame. The root `main.py` is a small compatibility wrapper that calls `src.main.run`. Game logic, UI screens, state persistence, scoring, and asset loading live under `src/`.

The desktop app uses:
- pygame for rendering, input, images, and music playback.
- Local JSON session storage under `%APPDATA%/tetris/session.json` on Windows, or `~/.tetris/session.json` elsewhere.
- FastAPI backend/database for active Season 2 accounts, score submission, history, and leaderboard.
- Google Sheets as an archived Season 1 top-3 leaderboard reader.
- Project-local assets under `assets/`.

### Backend/API

The backend is a FastAPI application in `backend/`. It provides nickname/password authentication, nickname changes, Season 2 score submission, global leaderboard, personal history, Telegram group leaderboard, and Telegram Mini App init data validation/linking. It uses SQLAlchemy and defaults to SQLite via `sqlite:///./tetris.db`, with `TETRIS_DATABASE_URL` available for an online database.

### Telegram Bot

`telegram_bot/` contains a python-telegram-bot scaffold. It exposes commands for launching the Mini App, showing leaderboards, and basic help. It depends on `TELEGRAM_BOT_TOKEN`, `BACKEND_URL`, and `MINI_APP_URL`.

### Telegram Mini App / Web Frontend

`webapp/` is a React + TypeScript + Vite scaffold. It renders a mobile-sized Tetris canvas with basic falling-block behavior, score display, touch controls, and keyboard hooks. It is not yet feature-equivalent with the pygame desktop game.

### Database/Storage

The backend uses SQLAlchemy models for users, scores, and refresh sessions. The default database is `tetris.db` in the repository root when running from the project directory. The desktop game records active Season 2 scores through the backend and keeps local session/settings data outside the repository.

### Assets

Images and music are now organized under the root `assets/` folder. No font files or short sound-effect files were found.

## Folder Structure

```text
.
|-- assets/
|   |-- audio/
|   |   |-- music/
|   |   |   |-- game-music.mp3
|   |   |   `-- menu-music.mp3
|   |   `-- sounds/
|   `-- images/
|       |-- background.png
|       |-- first_page.png
|       `-- main_menu.png
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   |-- security.py
|   |   `-- routers/
|   |-- README.md
|   `-- requirements.txt
|-- docs/
|   `-- PROJECT_STATE.md
|-- src/
|   |-- main.py
|   |-- assets.py
|   |-- config.py
|   |-- game/
|   |-- services/
|   |-- ui/
|   `-- utils/
|-- telegram_bot/
|   |-- bot.py
|   |-- README.md
|   `-- requirements.txt
|-- webapp/
|   |-- src/
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   `-- tsconfig.json
|-- .env.example
|-- .gitignore
|-- main.py
|-- main.spec
|-- README.md
|-- requirements.txt
`-- tetris.db
```

Generated and dependency folders also exist locally, including `venv/`, `webapp/node_modules/`, `build/`, `dist/`, `.idea/`, and `.git/`. They are not part of the active source layout.

## Main Entry Points

- `main.py` - desktop compatibility entry point; imports and runs `src.main.run`.
- `src/main.py` - pygame desktop app startup, main menu loop, music control, and screen routing.
- `backend/app/main.py` - FastAPI application entry point.
- `telegram_bot/bot.py` - Telegram bot polling entry point.
- `webapp/src/main.tsx` - React/Vite frontend entry point.
- `webapp/src/App.tsx` - Mini App shell and controls.
- `webapp/src/game/TetrisCanvas.tsx` - Mini App canvas scaffold.

## Dependencies

- `requirements.txt` - desktop dependencies: `pygame`, `requests`.
- `backend/requirements.txt` - API dependencies: FastAPI, uvicorn, SQLAlchemy, bcrypt, PyJWT, python-dotenv.
- `telegram_bot/requirements.txt` - bot dependencies: python-telegram-bot, httpx, python-dotenv.
- `webapp/package.json` and `webapp/package-lock.json` - React, Vite, TypeScript frontend dependencies and lockfile.
- `webapp/tsconfig.json` - TypeScript compiler configuration.
- `.env.example` - documented environment variables for backend and Telegram integration.
- `main.spec` - PyInstaller packaging configuration for the desktop app.

## Current Features

- Desktop pygame Tetris gameplay with falling pieces, movement, rotation, row clearing, scoring, game-over screen, and replay/menu flow.
- Desktop menu screens for player name entry, main menu, pause, settings, history, and leaderboard.
- Music playback for menu music, volume control, music enable/disable, pause/unpause behavior, and graceful audio-device fallback.
- Image loading for the first-page and background screens with fallback black surfaces if files are missing.
- Local session persistence for player name, music settings, cached leaderboard/history, local score history, and pending scores.
- Google Sheets leaderboard/history fetching and Google Forms score submission with retry and offline pending-score queue.
- FastAPI auth endpoints for registration, login, logout, and current user.
- FastAPI score endpoints for score submission, global leaderboard, personal history, and Telegram group leaderboard.
- Telegram init data validation and account-linking API endpoints.
- Telegram bot commands for `/start`, `/play`, `/leaderboard`, `/my_stats`, and `/help`.
- React/Vite Mini App scaffold with canvas rendering, score display, touch controls, and keyboard hooks.

## Asset Usage

### Images

Images found before refactor:
- `background.png` in the repository root.
- `first_page.png` in the repository root.
- `main_menu.png` in the repository root.

Images after refactor:
- `assets/images/background.png`
- `assets/images/first_page.png`
- `assets/images/main_menu.png`

`background.png` is referenced by `src/config.py`, resolved by `src/utils/resource_path.py`, loaded by `src/assets.py`, and displayed by `src/ui/menu.py` and `src/game/gameplay.py`.

`first_page.png` is referenced by `src/config.py`, resolved by `src/utils/resource_path.py`, loaded by `src/assets.py`, and displayed by `src/ui/menu.py` during player-name entry.

`main_menu.png` was found as an image asset but no active source reference was found. It was moved to `assets/images/` instead of deleted.

### Music/Sound

Music found before refactor:
- `menu-music.mp3` in the repository root.
- `game-music.mp3` in the repository root.

Music after refactor:
- `assets/audio/music/menu-music.mp3`
- `assets/audio/music/game-music.mp3`

Both music tracks are referenced by `src/config.py`, resolved by `src/utils/resource_path.py`, and validated by `src/assets.py`. `menu-music.mp3` is played through `pygame.mixer.music` in `src/main.py`; `game-music.mp3` is loaded into the asset bundle but is not currently started during gameplay.

No short sound-effect files were found. `assets/audio/sounds/` exists for future effects.

### Fonts

No project font files were found. The desktop app uses pygame system fonts through `pygame.font.SysFont`, and the webapp uses CSS font-family fallbacks.

### Packaging

`main.spec` now includes the whole `assets/` directory so PyInstaller builds keep the same runtime-relative layout used by source runs.

## Known Issues / Risks

- `main_menu.png` is currently unused. It may be an older menu image or future asset.
- `game-music.mp3` is referenced and validated, but gameplay currently stops menu music and does not start the game music track.
- The desktop score integration still contains hardcoded Google Sheets and Google Forms URLs in `src/config.py`.
- The backend default `TETRIS_SECRET_KEY` is a development placeholder and must be changed for production.
- Telegram validation requires `TELEGRAM_BOT_TOKEN`; the bot requires `TELEGRAM_BOT_TOKEN` and a real `MINI_APP_URL`.
- The local `tetris.db` file exists in the repository working tree, but `.gitignore` ignores database files.
- The web Mini App is a scaffold and does not yet match the full desktop gameplay.
- The webapp TypeScript build currently emits JavaScript files beside `webapp/src/*.tsx` before Vite builds because `tsconfig.json` does not set `noEmit` or an output directory.
- `build/` and `dist/` contain generated desktop build artifacts that may become stale after source or asset changes.
- `main.spec` is present but `*.spec` is ignored in `.gitignore`; keep that in mind if packaging config changes need to be committed in a fresh clone.

## Run Instructions

### Desktop Game

```bash
pip install -r requirements.txt
python main.py
```

### Backend/API

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Useful environment variables are documented in `.env.example` and `backend/README.md`.

### Telegram Bot

```bash
pip install -r telegram_bot/requirements.txt
python telegram_bot/bot.py
```

Set `TELEGRAM_BOT_TOKEN`, `BACKEND_URL`, and `MINI_APP_URL` before running.

### Web Mini App

```bash
cd webapp
npm install
npm run dev
```

For a production build:

```bash
cd webapp
npm run build
```

## Next Recommended Steps

1. Decide whether `main_menu.png` is still needed; either wire it into the UI or remove it in a dedicated cleanup after confirming it is unused.
2. Move Google Sheets/Form configuration out of `src/config.py` into environment-based settings.
3. Add automated tests for desktop game logic, score services, and backend API routes.
4. Bring the React Mini App gameplay closer to the desktop implementation.
5. Refresh PyInstaller `build/` and `dist/` artifacts after confirming the new asset layout.
