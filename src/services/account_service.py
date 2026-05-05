from __future__ import annotations

from typing import Optional

from src.state import AccountSession
from src.services.session_service import SessionService
from src.services.backend_client import BackendAuth, BackendClient, BackendClientError


class AccountService:
    """Desktop-side lightweight session storage for account identity."""

    def __init__(self, session_service: SessionService, backend_client: BackendClient) -> None:
        self.session_service = session_service
        self.backend_client = backend_client

    def load_account(self) -> Optional[AccountSession]:
        raw = self.session_service.load().get("account")
        if not isinstance(raw, dict):
            return None
        username = str(raw.get("username", "")).strip()
        if not username:
            return None
        account = AccountSession.from_dict(raw)
        self.backend_client.set_access_token(account.access_token)
        return account

    def save_account(self, account: AccountSession) -> None:
        data = self.session_service.load()
        data["account"] = account.to_dict()
        self.session_service.save(data)
        self.backend_client.set_access_token(account.access_token)

    def register(self, nickname: str, password: str) -> None:
        self.backend_client.register(nickname, password)

    def login(self, nickname: str, password: str) -> AccountSession:
        auth: BackendAuth = self.backend_client.login(nickname, password)
        user = self.backend_client.get_current_user()
        account = AccountSession(
            username=str(user.get("nickname", nickname)),
            user_id=int(user.get("id")) if user.get("id") is not None else None,
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
        )
        self.save_account(account)
        return account

    def refresh_current_user(self) -> Optional[dict]:
        account = self.load_account()
        if not account or not account.access_token:
            return None
        self.backend_client.set_access_token(account.access_token)
        try:
            user = self.backend_client.get_current_user()
        except BackendClientError as exc:
            if "unavailable" not in str(exc).lower():
                self.logout(local_only=True)
            return None
        account.username = str(user.get("nickname", account.username))
        account.user_id = int(user.get("id")) if user.get("id") is not None else account.user_id
        self.save_account(account)
        return user

    def change_nickname(self, nickname: str) -> AccountSession:
        result = self.backend_client.change_nickname(nickname)
        account = self.load_account() or AccountSession(username=str(result.get("nickname", nickname)))
        account.username = str(result.get("nickname", nickname))
        self.save_account(account)
        return account

    def logout(self, local_only: bool = False) -> None:
        account = self.load_account()
        if account and account.refresh_token and not local_only:
            try:
                self.backend_client.logout(account.refresh_token)
            except BackendClientError:
                pass
        data = self.session_service.load()
        data["account"] = None
        self.session_service.save(data)
        self.backend_client.set_access_token(None)
