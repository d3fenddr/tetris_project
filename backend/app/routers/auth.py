from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import RefreshSession, User
from backend.app.schemas import (
    LoginRequest,
    LogoutRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from backend.app.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    user = User(username=payload.username.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    user.last_login = datetime.utcnow()
    access_token = create_access_token(subject=str(user.id), extra_claims={"username": user.username})
    refresh_token = create_refresh_token()
    refresh = RefreshSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh)
    db.commit()
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    token_hash = hash_refresh_token(payload.refresh_token)
    refresh_session = (
        db.query(RefreshSession)
        .filter(
            RefreshSession.user_id == current_user.id,
            RefreshSession.refresh_token_hash == token_hash,
            RefreshSession.revoked_at.is_(None),
        )
        .first()
    )
    if refresh_session:
        refresh_session.revoked_at = datetime.utcnow()
        db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

