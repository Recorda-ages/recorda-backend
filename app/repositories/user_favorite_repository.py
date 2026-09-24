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


def get_genres_by_user(
    db: Session, user_ids: list[UUID]
) -> dict[UUID, dict[UUID, str]]:
    """Gêneros favoritos de vários usuários numa consulta só.

    Devolve {user_id: {genre_id: nome}} — o nome vem junto porque a sugestão
    por afinidade precisa exibir quais gêneros são comuns, não só contá-los.
    """
    if not user_ids:
        return {}

    stmt = (
        select(UserFavoriteGenre.user_id, Genre.genre_id, Genre.name)
        .join(Genre, Genre.genre_id == UserFavoriteGenre.genre_id)
        .where(UserFavoriteGenre.user_id.in_(user_ids))
    )

    genres_by_user: dict[UUID, dict[UUID, str]] = {}
    for user_id, genre_id, name in db.execute(stmt).all():
        genres_by_user.setdefault(user_id, {})[genre_id] = name
    return genres_by_user


def get_artists_by_user(
    db: Session, user_ids: list[UUID]
) -> dict[UUID, dict[str, str]]:
    """Artistas favoritos de vários usuários numa consulta só.

    Devolve {user_id: {deezer_artist_id: nome}}.
    """
    if not user_ids:
        return {}

    stmt = select(
        UserFavoriteArtist.user_id,
        UserFavoriteArtist.deezer_artist_id,
        UserFavoriteArtist.artist_name,
    ).where(UserFavoriteArtist.user_id.in_(user_ids))

    artists_by_user: dict[UUID, dict[str, str]] = {}
    for user_id, artist_id, name in db.execute(stmt).all():
        artists_by_user.setdefault(user_id, {})[artist_id] = name
    return artists_by_user
