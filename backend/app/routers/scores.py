from __future__ import annotations

from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Score, User
from backend.app.schemas import LeaderboardItem, ScoreCreateRequest, ScoreResponse

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
def create_score(
    payload: ScoreCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Score:
    score = Score(
        user_id=current_user.id,
        score=payload.score,
        platform=payload.platform,
        telegram_chat_id=payload.telegram_chat_id,
        client_game_id=payload.client_game_id,
    )
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
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LeaderboardItem]:
    rows = (
        db.query(
            User.username.label("username"),
            func.max(Score.score).label("score"),
            func.max(Score.created_at).label("best_at"),
        )
        .join(Score, Score.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(desc("score"))
        .limit(limit)
        .all()
    )
    return [LeaderboardItem(username=row.username, score=row.score, best_at=row.best_at) for row in rows]


@router.get("/history/me", response_model=list[ScoreResponse])
def my_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Score]:
    return (
        db.query(Score)
        .filter(Score.user_id == current_user.id)
        .order_by(Score.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/telegram/group/{chat_id}", response_model=list[LeaderboardItem])
def telegram_group_leaderboard(
    chat_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LeaderboardItem]:
    rows = (
        db.query(
            User.username.label("username"),
            func.max(Score.score).label("score"),
            func.max(Score.created_at).label("best_at"),
        )
        .join(User, User.id == Score.user_id)
        .filter(Score.telegram_chat_id == chat_id)
        .group_by(User.id, User.username)
        .order_by(desc("score"))
        .limit(limit)
        .all()
    )
    return [LeaderboardItem(username=row.username, score=row.score, best_at=row.best_at) for row in rows]

