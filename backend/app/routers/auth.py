from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.db_resilience import run_db_operation_with_retry
from backend.app.dependencies import get_current_user
from backend.app.models import RefreshSession, Score, User
from backend.app.nicknames import validate_available_nickname, validate_nickname_format, normalize_nickname
from backend.app.schemas import (
    AuthResponse,
    ChangeNicknameRequest,
    EnterRequest,
    EnterResponse,
    LoginRequest,
    LogoutRequest,
    NicknameChangeResponse,
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


def _rank_for_user(db: Session, user: User) -> int | None:
    best_score = (
        db.query(func.max(Score.score))
        .filter(Score.user_id == user.id, Score.season == settings.current_season)
        .scalar()
    )
    if best_score is None:
        return None
    better_count = (
        db.query(Score.user_id)
        .filter(Score.season == settings.current_season)
        .group_by(Score.user_id)
        .having(func.max(Score.score) > best_score)
        .count()
    )
    return better_count + 1


def _user_response(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        nickname=user.nickname,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        games_played=user.games_played or 0,
        best_score=user.best_score or 0,
        current_season_rank=_rank_for_user(db, user),
    )


def _token_pair_for_user(db: Session, user: User) -> TokenPairResponse:
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    access_token = create_access_token(subject=str(user.id), extra_claims={"nickname": user.nickname})
    refresh_token = create_refresh_token()
    refresh = RefreshSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


def _auth_response_for_user(db: Session, user: User, created: bool = False) -> AuthResponse:
    tokens = _token_pair_for_user(db, user)
    user_response = _user_response(db, user)
    db.commit()
    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        created=created,
        user=user_response,
    )


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    def operation() -> AuthResponse:
        nickname, normalized = validate_available_nickname(db, payload.nickname)

        user = User(
            nickname=nickname,
            normalized_nickname=normalized,
            password_hash=hash_password(payload.password),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()
        return _auth_response_for_user(db, user, created=True)

    try:
        return run_db_operation_with_retry(db, "auth/register", operation)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nickname is already taken.")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        clean_nickname = validate_nickname_format(payload.nickname)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid nickname or password.")

    def operation() -> AuthResponse:
        normalized = normalize_nickname(clean_nickname)
        user = db.query(User).filter(User.normalized_nickname == normalized).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found. Register first.")
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password.")
        return _auth_response_for_user(db, user, created=False)

    return run_db_operation_with_retry(db, "auth/login", operation)


@router.post("/enter", response_model=EnterResponse)
def enter(payload: EnterRequest, db: Session = Depends(get_db)) -> EnterResponse:
    def operation() -> EnterResponse:
        try:
            clean_nickname = validate_nickname_format(payload.nickname)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        normalized = normalize_nickname(clean_nickname)
        user = db.query(User).filter(User.normalized_nickname == normalized).first()
        created = False

        if user:
            if not verify_password(payload.password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid nickname or password.")
        else:
            try:
                nickname, normalized = validate_available_nickname(db, clean_nickname)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            user = User(
                nickname=nickname,
                normalized_nickname=normalized,
                password_hash=hash_password(payload.password),
                updated_at=datetime.utcnow(),
            )
            db.add(user)
            db.flush()
            created = True

        auth_response = _auth_response_for_user(db, user, created=created)
        return EnterResponse(
            access_token=auth_response.access_token,
            refresh_token=auth_response.refresh_token,
            token_type=auth_response.token_type,
            created=auth_response.created,
            user=auth_response.user,
        )

    try:
        return run_db_operation_with_retry(db, "auth/enter", operation)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nickname is already taken.")


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    def operation() -> dict:
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

    return run_db_operation_with_retry(db, "auth/logout", operation)


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    return run_db_operation_with_retry(db, "auth/me", lambda: _user_response(db, current_user))


@router.patch("/me/nickname", response_model=NicknameChangeResponse)
def change_nickname(
    payload: ChangeNicknameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NicknameChangeResponse:
    def operation() -> NicknameChangeResponse:
        nickname, normalized = validate_available_nickname(
            db,
            payload.nickname,
            exclude_user_id=current_user.id,
        )

        current_user.nickname = nickname
        current_user.normalized_nickname = normalized
        current_user.updated_at = datetime.utcnow()
        db.commit()
        return NicknameChangeResponse(
            id=current_user.id,
            nickname=current_user.nickname,
            message="Nickname updated. Future results will use the new nickname.",
        )

    try:
        return run_db_operation_with_retry(db, "auth/change-nickname", operation)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Nickname is already taken.")
