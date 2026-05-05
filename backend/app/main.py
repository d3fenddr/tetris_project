from __future__ import annotations

from fastapi import FastAPI

from backend.app.config import settings
from backend.app.database import Base, engine, ensure_schema
from backend.app.routers import auth, scores, telegram

app = FastAPI(title="Tetris Backend API", version=settings.app_version)
app.include_router(auth.router)
app.include_router(scores.router)
app.include_router(telegram.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    return {"version": settings.app_version}
