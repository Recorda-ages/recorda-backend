from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("users", "onboarding_completed", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("recordas", "user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
    ("recordas", "media_type", "VARCHAR"),
    ("recordas", "deezer_track_id", "VARCHAR"),
    ("recordas", "song_artist_name", "VARCHAR"),
    ("recordas", "song_cover_url", "VARCHAR"),
)


def init_db() -> None:
    from app import models  # noqa: F401  (register models on Base.metadata)

    Base.metadata.create_all(bind=engine)
    ensure_added_columns(engine)


def ensure_added_columns(bind: Engine) -> None:
    if bind.dialect.name != "postgresql":
        return
    with bind.begin() as connection:
        for table, column, definition in _ADDED_COLUMNS:
            connection.execute(
                text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"
                )
            )
