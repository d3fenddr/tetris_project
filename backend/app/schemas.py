from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=16)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    last_login: Optional[datetime]
    telegram_user_id: Optional[int]

    class Config:
        from_attributes = True


class ScoreCreateRequest(BaseModel):
    score: int = Field(ge=0, le=10_000_000)
    platform: Literal["desktop", "telegram_web"] = "desktop"
    telegram_chat_id: Optional[int] = None
    client_game_id: str = Field(min_length=8, max_length=64)


class ScoreResponse(BaseModel):
    id: int
    user_id: int
    score: int
    created_at: datetime
    platform: Literal["desktop", "telegram_web"]
    telegram_chat_id: Optional[int]
    client_game_id: str

    class Config:
        from_attributes = True


class LeaderboardItem(BaseModel):
    username: str
    score: int
    best_at: Optional[datetime]


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

