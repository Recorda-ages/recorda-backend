"""Persistence for the user's favourite genres and artists."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Genre, UserFavoriteArtist, UserFavoriteGenre


def replace_for_user(
    db: Session,
    user_id: UUID,
    genres: list[UserFavoriteGenre],
    artists: list[UserFavoriteArtist],
) -> None:
    db.execute(delete(UserFavoriteGenre).where(UserFavoriteGenre.user_id == user_id))
    db.execute(delete(UserFavoriteArtist).where(UserFavoriteArtist.user_id == user_id))
    db.add_all([*genres, *artists])
    db.commit()


def get_genres(db: Session, user_id: UUID) -> list[Genre]:
    stmt = (
        select(Genre)
        .join(UserFavoriteGenre, UserFavoriteGenre.genre_id == Genre.genre_id)
        .where(UserFavoriteGenre.user_id == user_id)
    )
    return list(db.scalars(stmt))


def get_artists(db: Session, user_id: UUID) -> list[UserFavoriteArtist]:
    stmt = select(UserFavoriteArtist).where(UserFavoriteArtist.user_id == user_id)
    return list(db.scalars(stmt))
