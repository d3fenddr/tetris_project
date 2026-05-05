from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def ensure_schema() -> None:
    """Small compatibility sync for local SQLite databases without migrations."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        user_additions = {
            "normalized_nickname": "ALTER TABLE users ADD COLUMN normalized_nickname VARCHAR(50)",
            "updated_at": "ALTER TABLE users ADD COLUMN updated_at DATETIME",
            "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME",
            "games_played": "ALTER TABLE users ADD COLUMN games_played INTEGER DEFAULT 0 NOT NULL",
            "best_score": "ALTER TABLE users ADD COLUMN best_score INTEGER DEFAULT 0 NOT NULL",
        }
        with engine.begin() as connection:
            for column_name, statement in user_additions.items():
                if column_name not in user_columns:
                    connection.execute(text(statement))
            connection.execute(text("UPDATE users SET normalized_nickname = lower(trim(username)) WHERE normalized_nickname IS NULL"))
            connection.execute(text("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL"))

    if "scores" in inspector.get_table_names():
        score_columns = {column["name"] for column in inspector.get_columns("scores")}
        score_additions = {
            "nickname_at_submission": "ALTER TABLE scores ADD COLUMN nickname_at_submission VARCHAR(50)",
            "lines": "ALTER TABLE scores ADD COLUMN lines INTEGER DEFAULT 0 NOT NULL",
            "level": "ALTER TABLE scores ADD COLUMN level INTEGER DEFAULT 1 NOT NULL",
            "mode": "ALTER TABLE scores ADD COLUMN mode VARCHAR(30) DEFAULT 'normal' NOT NULL",
            "season": "ALTER TABLE scores ADD COLUMN season INTEGER DEFAULT 2 NOT NULL",
        }
        with engine.begin() as connection:
            for column_name, statement in score_additions.items():
                if column_name not in score_columns:
                    connection.execute(text(statement))
            connection.execute(
                text(
                    "UPDATE scores SET nickname_at_submission = "
                    "(SELECT users.username FROM users WHERE users.id = scores.user_id) "
                    "WHERE nickname_at_submission IS NULL"
                )
            )


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
