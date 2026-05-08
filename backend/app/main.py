from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from backend.app.config import settings
from backend.app.database import Base, SessionLocal, check_database, engine, ensure_schema
from backend.app.routers import auth, scores, telegram

logger = logging.getLogger(__name__)


async def db_keepalive_loop() -> None:
    # This warms Neon while the Render service process is awake. It cannot prevent
    # Render free tier sleeping, because sleeping stops this application code too.
    interval = max(settings.db_keepalive_interval_seconds, 30)
    while True:
        try:
            await asyncio.to_thread(_run_db_keepalive_once)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("DB keepalive failed: %s", exc.__class__.__name__)
        await asyncio.sleep(interval)


def _run_db_keepalive_once() -> None:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema()
    except SQLAlchemyError as exc:
        logger.warning("Database startup sync failed: %s", exc.__class__.__name__)
    keepalive_task: asyncio.Task | None = None
    if settings.db_keepalive_enabled:
        keepalive_task = asyncio.create_task(db_keepalive_loop())
        logger.info("DB keepalive enabled with %s second interval.", settings.db_keepalive_interval_seconds)
    try:
        yield
    finally:
        if keepalive_task:
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                logger.info("DB keepalive stopped.")


app = FastAPI(title="Tetris Backend API", version=settings.app_version, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(scores.router)
app.include_router(telegram.router)


@app.get("/health")
def health() -> dict:
    if check_database():
        return {"status": "ok", "database": "ok"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "degraded", "database": "unavailable"},
    )


@app.get("/ping")
def ping() -> dict:
    return {"status": "ok"}


@app.head("/ping")
def ping_head() -> Response:
    return Response(status_code=status.HTTP_200_OK)


@app.get("/version")
def version() -> dict:
    return {"version": settings.app_version}
