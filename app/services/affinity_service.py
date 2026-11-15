from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.user_favorite_repository import get_artists, get_genres


def _get_musical_profile_items(db: Session, user_id: UUID) -> set:
    """Une os IDs de gêneros e artistas favoritados do usuário em um único conjunto."""
    genres = get_genres(db, user_id)
    artists = get_artists(db, user_id)
    return {genre.genre_id for genre in genres} | {
        artist.deezer_artist_id for artist in artists
    }


def calculate_affinity(db: Session, user_id_a: UUID, user_id_b: UUID) -> float:
    """
    Calcula a afinidade musical entre dois usuários (0 a 100), com base
    exclusivamente em gêneros e artistas favoritados no Perfil Musical.
    Música Favorita, curtidas e histórico não participam do cálculo.

    Assume que user_id_a e user_id_b são usuários válidos e ativos —
    essa validação é responsabilidade de quem chamar a função.
    """
    items_a = _get_musical_profile_items(db, user_id_a)
    items_b = _get_musical_profile_items(db, user_id_b)

    reference_count = min(len(items_a), len(items_b))
    if reference_count == 0:
        return 0.0

    hits = len(items_a & items_b)
    return (hits / reference_count) * 100
