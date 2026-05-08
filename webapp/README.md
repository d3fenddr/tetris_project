# Telegram Mini App

React + TypeScript + Vite Telegram Web App version of Tetris.

## Run locally
```bash
cd webapp
npm install
npm run dev
```

Set the backend URL for local development:
```bash
VITE_BACKEND_URL=http://localhost:8000
```

When opened outside Telegram on `localhost` or `127.0.0.1`, the app uses local debug mode so gameplay works without Telegram initData. Debug mode does not submit scores.

## Build
```bash
cd webapp
npm run build
```

The production files are written to `webapp/dist/`.

## Telegram deployment
- Deploy `webapp/dist/` to HTTPS static hosting.
- Set the deployed URL in the bot environment as `TELEGRAM_WEBAPP_URL`.
- Add the frontend origin to backend `TETRIS_CORS_ORIGINS`.
- The app authenticates by sending `Telegram.WebApp.initData` to `POST /telegram/auth`; the bot token stays only on the backend.

## Controls
- Desktop: arrow keys, Space hard drop, Enter/Escape pause.
- Mobile: swipe left/right/down/up, plus on-screen buttons.
- Holding Left, Right, Down, and Rotate repeats. Mobile hard drop is intentionally not shown.
