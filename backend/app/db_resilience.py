from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")
DEFAULT_DB_UNAVAILABLE_DETAIL = "Database is temporarily unavailable. Please try again."


def db_unavailable_response(endpoint: str, db: Session, exc: SQLAlchemyError, detail: str = DEFAULT_DB_UNAVAILABLE_DETAIL) -> None:
    db.rollback()
    logger.warning("Database unavailable during %s: %s", endpoint, exc.__class__.__name__)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def run_db_operation_with_retry(
    db: Session,
    endpoint: str,
    operation: Callable[[], T],
    detail: str = DEFAULT_DB_UNAVAILABLE_DETAIL,
    retries: int = 1,
    backoff_seconds: float = 0.5,
) -> T:
    for attempt in range(retries + 1):
        try:
            return operation()
        except IntegrityError:
            db.rollback()
            raise
        except OperationalError as exc:
            db.rollback()
            logger.warning("Transient database error during %s: %s", endpoint, exc.__class__.__name__)
            if attempt < retries:
                time.sleep(backoff_seconds)
                continue
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail) from exc
        except DatabaseError as exc:
            db_unavailable_response(endpoint, db, exc, detail)
        except SQLAlchemyError as exc:
            db_unavailable_response(endpoint, db, exc, detail)

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
