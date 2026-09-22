"""Business logic for the onboarding music preferences."""

from sqlalchemy.orm import Session

from app.models import AppUser, Genre, UserFavoriteArtist, UserFavoriteGenre
from app.repositories import genre_repository, user_favorite_repository
from app.schemas.music_preference import (
    FavoriteTrack,
    MusicItem,
    MusicPreferencesCreate,
    MusicPreferencesRead,
)


def replace_for_user(
    db: Session, user: AppUser, payload: MusicPreferencesCreate
) -> MusicPreferencesRead:
    """Persist the onboarding selection, replacing any previous one."""
    genres = resolve_genres(db, payload.genres)
    favorite_genres = [
        UserFavoriteGenre(user_id=user.user_id, genre_id=genre.genre_id)
        for genre in genres
    ]
    favorite_artists = [
        UserFavoriteArtist(
            user_id=user.user_id,
            deezer_artist_id=str(artist.deezer_id),
            artist_name=artist.name,
            artist_image_url=artist.picture_url,
        )
        for artist in payload.artists
    ]
    _set_favorite_track(user, payload.favorite_track)
    user_favorite_repository.replace_for_user(
        db, user.user_id, favorite_genres, favorite_artists
    )

    return MusicPreferencesRead(
        genres=payload.genres,
        artists=payload.artists,
        favorite_track=payload.favorite_track,
        onboarding_completed=user.onboarding_completed,
    )


def resolve_genres(db: Session, items: list[MusicItem]) -> list[Genre]:
    """Map Deezer genres onto rows of the genre vocabulary, adding missing ones.

    A Deezer genre is matched first by its id and then by name, so the seeded
    genres that share a name with Deezer (Pop, Rock, Jazz...) are reused.
    """
    by_deezer_id = {
        genre.deezer_genre_id: genre
        for genre in genre_repository.get_by_deezer_ids(
            db, [str(item.deezer_id) for item in items]
        )
    }
    by_name = {
        genre.name: genre
        for genre in genre_repository.get_by_names(db, [item.name for item in items])
    }

    resolved = []
    for item in items:
        genre = by_deezer_id.get(str(item.deezer_id)) or by_name.get(item.name)
        if genre is None:
            genre = Genre(name=item.name)
            db.add(genre)
        genre.deezer_genre_id = str(item.deezer_id)
        genre.picture_url = item.picture_url or genre.picture_url
        resolved.append(genre)
    db.flush()
    return resolved


def _set_favorite_track(user: AppUser, track: FavoriteTrack) -> None:
    user.fav_song_deezer_track_id = str(track.deezer_id)
    user.fav_song_title = track.title
    user.fav_song_artist_name = track.artist_name
    user.fav_song_cover_url = track.cover_url
    user.fav_song_preview_url = track.preview_url
