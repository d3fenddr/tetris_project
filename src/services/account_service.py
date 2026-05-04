from __future__ import annotations

from typing import Optional

from src.state import AccountSession
from src.services.session_service import SessionService


class AccountService:
    """Desktop-side lightweight session storage for account identity."""

    def __init__(self, session_service: SessionService) -> None:
        self.session_service = session_service

    def load_account(self) -> Optional[AccountSession]:
        raw = self.session_service.load().get("account")
        if not isinstance(raw, dict):
            return None
        username = str(raw.get("username", "")).strip()
        if not username:
            return None
        return AccountSession.from_dict(raw)

    def save_account(self, account: AccountSession) -> None:
        data = self.session_service.load()
        data["account"] = account.to_dict()
        self.session_service.save(data)

    def logout(self) -> None:
        data = self.session_service.load()
        data["account"] = None
        self.session_service.save(data)

