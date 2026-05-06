from __future__ import annotations

from datetime import datetime
import time

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import Score, User
from backend.app.schemas import LeaderboardItem, ScoreCreateRequest, ScoreResponse

router = APIRouter(prefix="/scores", tags=["scores"])

VALID_GAME_MODES = {"peaceful", "easy", "normal", "hard"}
SCORE_WRITE_RETRIES = 2
SCORE_WRITE_BACKOFF_SECONDS = 0.25


def _leaderboard_item(rank: int, row: Score) -> LeaderboardItem:
    return LeaderboardItem(
        rank=rank,
        user_id=row.user_id,
        nickname=row.nickname_at_submission or row.user.nickname,
        score=row.score,
        mode=row.mode,
        lines=row.lines,
        level=row.level,
        season=row.season,
        created_at=row.created_at,
    )


@router.post("", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
def create_score(
    payload: ScoreCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Score:
    if settings.debug_online_score_flow:
        print(
            "[score-flow] Backend score submit received: "
            f"user_id={current_user.id}, score={payload.score}, mode={payload.mode}, "
            f"lines={payload.lines}, level={payload.level}, season={payload.season}"
        )
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
    for attempt in range(SCORE_WRITE_RETRIES + 1):
        try:
            db.commit()
            db.refresh(score)
            if settings.debug_online_score_flow:
                print(f"[score-flow] Backend score saved: id={score.id}, user_id={current_user.id}")
            return score
        except IntegrityError:
            db.rollback()
            if settings.debug_online_score_flow:
                print(f"[score-flow] Backend duplicate score submission: user_id={current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate score submission for this game session.",
            )
        except OperationalError as exc:
            db.rollback()
            if attempt < SCORE_WRITE_RETRIES:
                if settings.debug_online_score_flow:
                    print(
                        "[score-flow] Backend score save transient failure: "
                        f"{exc.__class__.__name__}, retry {attempt + 1}/{SCORE_WRITE_RETRIES}"
                    )
                time.sleep(SCORE_WRITE_BACKOFF_SECONDS * (attempt + 1))
                db.add(score)
                continue
            print(f"[score-flow] Backend score save failed after retries: {exc.__class__.__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Score database is temporarily unavailable. Please try again.",
            )
        except SQLAlchemyError as exc:
            db.rollback()
            print(f"[score-flow] Backend score save failed: {exc.__class__.__name__}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Score database is temporarily unavailable. Please try again.",
            )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Score database is temporarily unavailable. Please try again.",
    )


@router.get("/leaderboard", response_model=list[LeaderboardItem])
def global_leaderboard(
    db: Session = Depends(get_db),
    season: int = Query(default=settings.current_season, ge=1, le=99),
    limit: int = Query(default=10, ge=1, le=100),
    mode: str | None = Query(default=None, min_length=1, max_length=30),
) -> list[LeaderboardItem]:
    if settings.debug_online_score_flow:
        print(f"[score-flow] Backend leaderboard fetch: season={season}, mode={mode or 'all'}, limit={limit}")
    clean_mode = mode.lower() if mode else "all"
    query = db.query(Score).filter(Score.season == season)
    if clean_mode != "all":
        if clean_mode not in VALID_GAME_MODES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid leaderboard mode.")
        query = query.filter(Score.mode == clean_mode)

    try:
        candidate_rows = (
            query.order_by(
                Score.score.desc(),
                Score.created_at.asc(),
                Score.id.asc(),
            )
            .all()
        )
    except SQLAlchemyError as exc:
        print(f"[score-flow] Backend leaderboard fetch failed: {exc.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leaderboard database is temporarily unavailable. Please try again.",
        )

    best_rows: list[Score] = []
    seen_keys: set[tuple[int, str]] = set()
    for row in candidate_rows:
        key = (row.user_id, row.mode)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        best_rows.append(row)
        if len(best_rows) >= limit:
            break

    if settings.debug_online_score_flow:
        print(f"[score-flow] Backend leaderboard rows: {len(best_rows)}")
    return [_leaderboard_item(idx, row) for idx, row in enumerate(best_rows, start=1)]


@router.get("/history/me", response_model=list[ScoreResponse])
def my_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    season: int = Query(default=settings.current_season, ge=1, le=99),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Score]:
    if settings.debug_online_score_flow:
        print(f"[score-flow] Backend history fetch: user_id={current_user.id}, season={season}, limit={limit}")
    try:
        rows = (
            db.query(Score)
            .filter(Score.user_id == current_user.id, Score.season == season)
            .order_by(Score.created_at.desc())
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        print(f"[score-flow] Backend history fetch failed: {exc.__class__.__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="History database is temporarily unavailable. Please try again.",
        )
    if settings.debug_online_score_flow:
        print(f"[score-flow] Backend history rows: {len(rows)}")
    return rows


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
        .order_by(Score.score.desc(), Score.created_at.asc(), Score.id.asc())
        .limit(limit)
        .all()
    )
    return [_leaderboard_item(idx, row) for idx, row in enumerate(rows, start=1)]
