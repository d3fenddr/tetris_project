from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.config import settings


class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class EnterRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class ChangeNicknameRequest(BaseModel):
    nickname: str = Field(min_length=3, max_length=20)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    nickname: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    games_played: int = 0
    best_score: int = 0
    current_season_rank: Optional[int] = None

    class Config:
        from_attributes = True


class AuthResponse(TokenPairResponse):
    created: bool = False
    user: UserResponse


class EnterResponse(AuthResponse):
    pass


class NicknameChangeResponse(BaseModel):
    id: int
    nickname: str
    message: str


class ScoreCreateRequest(BaseModel):
    score: int = Field(ge=0, le=10_000_000)
    lines: int = Field(default=0, ge=0, le=10_000)
    level: int = Field(default=1, ge=1, le=1_000)
    mode: str = Field(default="normal", min_length=1, max_length=30)
    season: int = Field(default=settings.current_season, ge=1, le=99)
    platform: Literal["desktop", "telegram_web"] = "desktop"
    telegram_chat_id: Optional[int] = None
    client_game_id: str = Field(min_length=8, max_length=64)


class ScoreResponse(BaseModel):
    id: int
    user_id: int
    nickname_at_submission: Optional[str]
    score: int
    lines: int
    level: int
    mode: str
    season: int
    created_at: datetime
    platform: Literal["desktop", "telegram_web"]
    telegram_chat_id: Optional[int]
    client_game_id: str

    class Config:
        from_attributes = True


class LeaderboardItem(BaseModel):
    rank: int
    nickname: str
    score: int
    mode: str
    lines: int
    created_at: datetime


class TelegramInitDataRequest(BaseModel):
    init_data: str = Field(min_length=10)


class TelegramValidationResponse(BaseModel):
    valid: bool
    telegram_user_id: Optional[int] = None
    username: Optional[str] = None
    auth_date: Optional[int] = None
    message: Optional[str] = None


class TelegramLinkResponse(BaseModel):
    linked: bool
    telegram_user_id: Optional[int] = None
    message: str
