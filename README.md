# Tetris Project (Desktop + Telegram Migration)

## Current Desktop App
- Entry point: `main.py` (compat wrapper)
- Modular source: `src/`
- Existing assets preserved:
  - `background.png`
  - `first_page.png`
  - `menu-music.mp3`
  - `game-music.mp3`

Run desktop:
```bash
pip install -r requirements.txt
python main.py
```

## New Architecture Scaffolds
- `backend/` - FastAPI + SQLAlchemy API
- `telegram_bot/` - Telegram bot command scaffold
- `webapp/` - React + TypeScript Mini App scaffold

## Notes
- Pygame desktop gameplay is preserved.
- Google Sheets remains a temporary score adapter for desktop.
- Backend/database flow is ready for migration from Google Sheets.
- Use environment variables for all secrets/tokens (see `.env.example`).

