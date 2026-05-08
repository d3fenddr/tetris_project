from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def main() -> None:
    load_dotenv(ROOT_DIR / ".env")
    token = require_env("TELEGRAM_BOT_TOKEN")
    backend_url = require_env("BACKEND_URL").rstrip("/")
    secret = require_env("TELEGRAM_WEBHOOK_SECRET")
    webhook_url = f"{backend_url}/telegram/bot/webhook/{secret}"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"
    body = urlencode({"url": webhook_url}).encode("utf-8")
    request = Request(api_url, data=body, method="POST")
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("ok"):
        print(f"Webhook set to {backend_url}/telegram/bot/webhook/<secret>")
    else:
        print(f"Webhook setup failed: {payload.get('description', 'unknown error')}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
