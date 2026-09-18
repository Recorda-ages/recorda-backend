"""Persistence and query access for the Genre vocabulary."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Genre


def get_by_deezer_ids(db: Session, deezer_ids: list[str]) -> list[Genre]:
    stmt = select(Genre).where(Genre.deezer_genre_id.in_(deezer_ids))
    return list(db.scalars(stmt))


def get_by_names(db: Session, names: list[str]) -> list[Genre]:
    return list(db.scalars(select(Genre).where(Genre.name.in_(names))))
