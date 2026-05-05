from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column("username", String(50), unique=True, nullable=False, index=True)
    normalized_nickname = Column(String(50), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    games_played = Column(Integer, nullable=False, default=0)
    best_score = Column(Integer, nullable=False, default=0)
    telegram_user_id = Column(BigInteger, unique=True, nullable=True, index=True)

    scores = relationship("Score", back_populates="user", cascade="all, delete-orphan")
    refresh_sessions = relationship(
        "RefreshSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nickname_at_submission = Column(String(50), nullable=True)
    score = Column(Integer, nullable=False)
    lines = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1)
    mode = Column(String(30), nullable=False, default="normal")
    season = Column(Integer, nullable=False, default=2, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    platform = Column(
        Enum("desktop", "telegram_web", name="score_platform"),
        nullable=False,
        default="desktop",
    )
    telegram_chat_id = Column(BigInteger, nullable=True, index=True)
    client_game_id = Column(String(36), nullable=False, default=lambda: str(uuid4()))

    user = relationship("User", back_populates="scores")

    __table_args__ = (
        UniqueConstraint("user_id", "client_game_id", name="uq_scores_user_game_id"),
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="refresh_sessions")
