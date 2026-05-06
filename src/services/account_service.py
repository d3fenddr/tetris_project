from __future__ import annotations

from typing import Optional

from src.state import AccountSession
from src.services.session_service import SessionService
from src.config import DEBUG_ONLINE_SCORE_FLOW
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
        if DEBUG_ONLINE_SCORE_FLOW:
            print("[score-flow] Account session save completed.")

    def _account_from_auth(self, nickname: str, auth: BackendAuth) -> AccountSession:
        user = auth.user or self.backend_client.get_current_user()
        account = AccountSession(
            username=str(user.get("nickname", nickname)),
            user_id=int(user.get("id")) if user.get("id") is not None else None,
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
        )
        self.save_account(account)
        if DEBUG_ONLINE_SCORE_FLOW:
            print(
                "[score-flow] Account session saved: "
                f"user={account.username}, user_id={account.user_id}, authenticated={bool(account.access_token)}"
            )
        return account

    def register(self, nickname: str, password: str) -> AccountSession:
        if DEBUG_ONLINE_SCORE_FLOW:
            print("[score-flow] Auth action: register")
        try:
            auth = self.backend_client.register(nickname, password)
        except BackendClientError as exc:
            if not exc.is_unavailable:
                raise
            if DEBUG_ONLINE_SCORE_FLOW:
                print("[score-flow] Register uncertain, attempting one login recovery.")
            try:
                auth = self.backend_client.login(nickname, password)
                if DEBUG_ONLINE_SCORE_FLOW:
                    print("[score-flow] Register uncertain, login recovery succeeded.")
            except BackendClientError as login_exc:
                if DEBUG_ONLINE_SCORE_FLOW:
                    print(f"[score-flow] Register recovery failed: {login_exc.error_type}")
                if login_exc.is_unavailable:
                    raise BackendClientError(
                        "Backend is unavailable. Registration may have completed. Try Login.",
                        error_type="network",
                    ) from login_exc
                raise login_exc
        return self._account_from_auth(nickname, auth)

    def login(self, nickname: str, password: str) -> AccountSession:
        if DEBUG_ONLINE_SCORE_FLOW:
            print("[score-flow] Auth action: login")
        auth: BackendAuth = self.backend_client.login(nickname, password)
        return self._account_from_auth(nickname, auth)

    def authenticate_or_register(self, nickname: str, password: str) -> tuple[AccountSession, bool]:
        auth = self.backend_client.authenticate_or_register(nickname, password)
        account = self._account_from_auth(nickname, auth)
        return account, auth.created

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
