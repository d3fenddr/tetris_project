from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import settings


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgresql+psycopg2://", "postgres://"))


def _normalized_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _postgres_connect_args(database_url: str) -> dict:
    parsed = urlsplit(database_url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if any(key.lower() == "sslmode" for key, _value in query_pairs):
        return {}
    return {"sslmode": "require"}


def _engine_kwargs(database_url: str) -> tuple[str, dict]:
    kwargs: dict = {"future": True}
    if _is_sqlite_url(database_url):
        kwargs["connect_args"] = {"check_same_thread": False}
        return database_url, kwargs

    if _is_postgres_url(database_url):
        kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "pool_size": 5,
                "max_overflow": 10,
            }
        )
        kwargs["connect_args"] = _postgres_connect_args(database_url)
        return _normalized_database_url(database_url), kwargs

    return database_url, kwargs


database_url, engine_kwargs = _engine_kwargs(settings.database_url)
engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()


def _column_type(sqlite_type: str, postgres_type: str) -> str:
    return sqlite_type if _is_sqlite_url(settings.database_url) else postgres_type


def ensure_schema() -> None:
    """Small compatibility sync for existing databases without migrations."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        user_additions = {
            "normalized_nickname": "ALTER TABLE users ADD COLUMN normalized_nickname VARCHAR(50)",
            "updated_at": f"ALTER TABLE users ADD COLUMN updated_at {_column_type('DATETIME', 'TIMESTAMP')}",
            "last_login_at": f"ALTER TABLE users ADD COLUMN last_login_at {_column_type('DATETIME', 'TIMESTAMP')}",
            "games_played": "ALTER TABLE users ADD COLUMN games_played INTEGER DEFAULT 0 NOT NULL",
            "best_score": "ALTER TABLE users ADD COLUMN best_score INTEGER DEFAULT 0 NOT NULL",
            "telegram_user_id": f"ALTER TABLE users ADD COLUMN telegram_user_id {_column_type('BIGINT', 'BIGINT')}",
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
            "created_at": f"ALTER TABLE scores ADD COLUMN created_at {_column_type('DATETIME', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL')}",
            "nickname_at_submission": "ALTER TABLE scores ADD COLUMN nickname_at_submission VARCHAR(50)",
            "lines": "ALTER TABLE scores ADD COLUMN lines INTEGER DEFAULT 0 NOT NULL",
            "level": "ALTER TABLE scores ADD COLUMN level INTEGER DEFAULT 1 NOT NULL",
            "mode": "ALTER TABLE scores ADD COLUMN mode VARCHAR(30) DEFAULT 'normal' NOT NULL",
            "season": "ALTER TABLE scores ADD COLUMN season INTEGER DEFAULT 2 NOT NULL",
            "platform": "ALTER TABLE scores ADD COLUMN platform VARCHAR(30) DEFAULT 'desktop' NOT NULL",
            "telegram_chat_id": f"ALTER TABLE scores ADD COLUMN telegram_chat_id {_column_type('BIGINT', 'BIGINT')}",
            "client_game_id": "ALTER TABLE scores ADD COLUMN client_game_id VARCHAR(64) DEFAULT 'legacy' NOT NULL",
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
