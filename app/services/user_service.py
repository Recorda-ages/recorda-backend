"""Business logic and orchestration for the AppUser entity."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core import security
from app.models import AppUser
from app.models.app_user import ROLE_USER
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING
from app.repositories import (
    recorda_repository,
    user_favorite_repository,
    user_repository,
)
from app.schemas.user import (
    ProfileArtist,
    ProfileFavoriteSong,
    ProfileGenre,
    SuggestedUser,
    UserChangeRole,
    UserCreate,
    UserProfileRead,
    UserSearchResult,
    UserUpdate,
)
from app.services import affinity_service

USERNAME_TAKEN_MESSAGE = "Este usuário já está cadastrado."
EMAIL_TAKEN_MESSAGE = "Este email já está cadastrado."
USER_ALREADY_EXISTS_MESSAGE = "Usuário ou email já cadastrado"
DEFAULT_SUGGESTION_LIMIT = 20

_FOLLOW_STATUS_MAP = {
    STATUS_ACCEPTED: "seguindo",
    STATUS_PENDING: "solicitado",
    None: "nenhuma",
}


class UserAlreadyExistsError(Exception):
    def __init__(self, fields: list[dict[str, str]]) -> None:
        super().__init__(USER_ALREADY_EXISTS_MESSAGE)
        self.fields = fields


class IncompleteProfileError(Exception):
    """Raised when a user has not completed the music onboarding yet."""


def get_all(db: Session) -> list[AppUser]:
    return user_repository.get_all(db)


def get_by_id(db: Session, user_id: UUID) -> AppUser | None:
    return user_repository.get_by_id(db, user_id)


def get_own_profile(db: Session, user: AppUser) -> UserProfileRead:
    """Return the complete profile contract consumed by the profile screen."""
    if (
        user.fav_song_deezer_track_id is None
        or user.fav_song_title is None
        or user.fav_song_artist_name is None
        or user.fav_song_cover_url is None
    ):
        raise IncompleteProfileError

    genres = user_favorite_repository.get_genres(db, user.user_id)
    artists = user_favorite_repository.get_artists(db, user.user_id)
    recordas = recorda_repository.list_by_user(db, user.user_id)
    return UserProfileRead(
        user_id=user.user_id,
        username=user.username,
        name=user.name,
        profile_picture_url=user.profile_picture_url,
        favorite_song=ProfileFavoriteSong(
            deezer_track_id=user.fav_song_deezer_track_id,
            title=user.fav_song_title,
            artist_name=user.fav_song_artist_name,
            cover_url=user.fav_song_cover_url,
            preview_url=user.fav_song_preview_url,
        ),
        favorite_genres=[
            ProfileGenre(genre_id=genre.genre_id, name=genre.name) for genre in genres
        ],
        favorite_artists=[
            ProfileArtist(
                deezer_artist_id=artist.deezer_artist_id,
                name=artist.artist_name,
                image_url=artist.artist_image_url,
            )
            for artist in artists
        ],
        recordas=recordas,
    )


def create(db: Session, payload: UserCreate) -> AppUser:
    ensure_unique_credentials(db, payload.username, payload.email)
    user = AppUser(
        name=payload.name,
        email=payload.email,
        username=payload.username,
        password_hash=security.hash_password(payload.password),
        role=ROLE_USER,
    )
    return user_repository.create(db, user)


def ensure_unique_credentials(db: Session, username: str, email: str) -> None:
    fields = []
    if user_repository.get_by_username(db, username, include_deleted=True):
        fields.append({"field": "username", "message": USERNAME_TAKEN_MESSAGE})
    if user_repository.get_by_email(db, email, include_deleted=True):
        fields.append({"field": "email", "message": EMAIL_TAKEN_MESSAGE})
    if fields:
        raise UserAlreadyExistsError(fields)


def update(db: Session, user_id: UUID, payload: UserUpdate) -> AppUser | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    return user_repository.save(db, user)


def delete(db: Session, user_id: UUID) -> bool:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return False
    user_repository.soft_delete(db, user)
    return True


def change_role(db: Session, user_id: UUID, payload: UserChangeRole) -> AppUser | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    user.role = payload.role
    return user_repository.save(db, user)


def search_by_username(
    db: Session, query: str, current_user_id: UUID
) -> list[UserSearchResult]:
    stripped_query = query.strip()
    if not stripped_query:
        return []

    results = user_repository.search_by_username(db, stripped_query, current_user_id)
    return [
        UserSearchResult(
            user_id=user.user_id,
            username=user.username,
            avatar_url=user.profile_picture_url,
            follow_status=_FOLLOW_STATUS_MAP[raw_status],
        )
        for user, raw_status in results
    ]


def suggest_by_affinity(
    db: Session, current_user_id: UUID, limit: int = DEFAULT_SUGGESTION_LIMIT
) -> list[SuggestedUser]:
    """Perfis sugeridos por afinidade musical, do mais afim para o menos (US27).

    Só entram usuários com afinidade maior que zero: sem nada em comum não há
    o que sugerir, nem o que exibir como gênero/artista compartilhado.

    ponytail: pontua chamando `calculate_affinity` uma vez por candidato, o
    que custa duas consultas por candidato. É o preço de usar o cálculo do
    Épico 4 sem alterá-lo; se a base crescer, a saída é a afinidade expor uma
    função que receba os conjuntos já carregados.
    """
    my_genres = {
        genre.genre_id: genre.name
        for genre in user_favorite_repository.get_genres(db, current_user_id)
    }
    my_artists = {
        artist.deezer_artist_id: artist.artist_name
        for artist in user_favorite_repository.get_artists(db, current_user_id)
    }

    # Sem perfil musical a afinidade com qualquer um é zero; poupa as consultas.
    if not my_genres and not my_artists:
        return []

    candidates = user_repository.list_suggestion_candidates(db, current_user_id)
    if not candidates:
        return []

    candidate_ids = [candidate.user_id for candidate in candidates]
    genres_by_user = user_favorite_repository.get_genres_by_user(db, candidate_ids)
    artists_by_user = user_favorite_repository.get_artists_by_user(db, candidate_ids)

    suggestions = []
    for candidate in candidates:
        score = affinity_service.calculate_affinity(
            db, current_user_id, candidate.user_id
        )
        if score <= 0:
            continue

        their_genres = genres_by_user.get(candidate.user_id, {})
        their_artists = artists_by_user.get(candidate.user_id, {})
        suggestions.append(
            SuggestedUser(
                user_id=candidate.user_id,
                username=candidate.username,
                avatar_url=candidate.profile_picture_url,
                affinity=score,
                common_genres=sorted(
                    my_genres[genre_id]
                    for genre_id in my_genres.keys() & their_genres.keys()
                ),
                common_artists=sorted(
                    my_artists[artist_id]
                    for artist_id in my_artists.keys() & their_artists.keys()
                ),
            )
        )

    # Username desempata para a ordem ser estável entre requisições iguais.
    suggestions.sort(key=lambda suggestion: (-suggestion.affinity, suggestion.username))
    return suggestions[:limit]
