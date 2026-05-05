from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Score, User
from backend.app.schemas import LeaderboardItem, ScoreCreateRequest, ScoreResponse

router = APIRouter(prefix="/scores", tags=["scores"])

VALID_GAME_MODES = {"peaceful", "easy", "normal", "hard"}


@router.post("", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
def create_score(
    payload: ScoreCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Score:
    if payload.season != settings.current_season:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New scores can only be submitted to Season {settings.current_season}.",
        )
    if payload.mode not in VALID_GAME_MODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid game mode.")

    score = Score(
        user_id=current_user.id,
        nickname_at_submission=current_user.nickname,
        score=payload.score,
        lines=payload.lines,
        level=payload.level,
        mode=payload.mode,
        season=settings.current_season,
        platform=payload.platform,
        telegram_chat_id=payload.telegram_chat_id,
        client_game_id=payload.client_game_id,
    )
    current_user.games_played = (current_user.games_played or 0) + 1
    current_user.best_score = max(current_user.best_score or 0, payload.score)
    current_user.updated_at = datetime.utcnow()
    db.add(score)
    try:
        db.commit()
        db.refresh(score)
        return score
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate score submission for this game session.",
        )


@router.get("/leaderboard", response_model=list[LeaderboardItem])
def global_leaderboard(
    db: Session = Depends(get_db),
    season: int = Query(default=settings.current_season, ge=1, le=99),
    limit: int = Query(default=10, ge=1, le=100),
    mode: str | None = Query(default=None, min_length=1, max_length=30),
) -> list[LeaderboardItem]:
    query = db.query(Score).filter(Score.season == season)
    if mode and mode.lower() != "all":
        clean_mode = mode.lower()
        if clean_mode not in VALID_GAME_MODES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid leaderboard mode.")
        query = query.filter(Score.mode == clean_mode)

    rows = query.order_by(desc(Score.score), Score.created_at.asc()).limit(limit).all()
    return [
        LeaderboardItem(
            rank=idx,
            nickname=row.nickname_at_submission or row.user.nickname,
            score=row.score,
            mode=row.mode,
            lines=row.lines,
            created_at=row.created_at,
        )
        for idx, row in enumerate(rows, start=1)
    ]


@router.get("/history/me", response_model=list[ScoreResponse])
def my_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    season: int = Query(default=settings.current_season, ge=1, le=99),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Score]:
    return (
        db.query(Score)
        .filter(Score.user_id == current_user.id, Score.season == season)
        .order_by(Score.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/telegram/group/{chat_id}", response_model=list[LeaderboardItem])
def telegram_group_leaderboard(
    chat_id: int,
    db: Session = Depends(get_db),
    season: int = Query(default=settings.current_season, ge=1, le=99),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LeaderboardItem]:
    rows = (
        db.query(Score)
        .filter(Score.telegram_chat_id == chat_id, Score.season == season)
        .order_by(desc(Score.score), Score.created_at.asc())
        .limit(limit)
        .all()
    )
    return [
        LeaderboardItem(
            rank=idx,
            nickname=row.nickname_at_submission or row.user.nickname,
            score=row.score,
            mode=row.mode,
            lines=row.lines,
            created_at=row.created_at,
        )
        for idx, row in enumerate(rows, start=1)
    ]
