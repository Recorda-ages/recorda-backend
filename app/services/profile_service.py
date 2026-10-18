"""Montagem do cabeçalho do perfil (contrato ProfileRead, C-2 do Épico 06)."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.music_preview import public_preview_url
from app.models import AppUser
from app.repositories import follow_repository, recorda_repository
from app.schemas.profile import (
    ProfileCounts,
    ProfileFavoriteSong,
    ProfileRead,
    ProfileRelationship,
)


class IncompleteProfileError(Exception):
    """O usuário ainda não concluiu o onboarding musical."""


def count_recordas(db: Session, user_id: UUID) -> int:
    """Recordas vivas: exclusões pelo autor e pela moderação não contam."""
    return recorda_repository.count_by_user(db, user_id)


def count_followers(db: Session, user_id: UUID) -> int:
    return follow_repository.count_followers(db, user_id)


def count_following(db: Session, user_id: UUID) -> int:
    return follow_repository.count_following(db, user_id)


def build_profile(db: Session, owner: AppUser, viewer: AppUser) -> ProfileRead:
    """Cabeçalho do perfil de `owner` visto por `viewer`.

    Por enquanto só o perfil próprio (`owner == viewer`). Relação e privacidade
    para terceiros entram na T-E6.US29.BE.01; o streak, na T-E6.US35.BE.01.
    """
    if owner.user_id != viewer.user_id:
        raise NotImplementedError("Perfil de terceiros: T-E6.US29.BE.01")

    return ProfileRead(
        user_id=owner.user_id,
        name=owner.name,
        username=owner.username,
        profile_picture_url=owner.profile_picture_url,
        is_private=owner.is_private,
        counts=_build_counts(db, owner.user_id),
        favorite_song=_build_favorite_song(owner),
        streak=None,
        relationship=ProfileRelationship(
            is_self=True, follow_status="nenhuma", follow_id=None
        ),
        can_view_content=True,
    )


def _build_counts(db: Session, user_id: UUID) -> ProfileCounts:
    return ProfileCounts(
        recordas=count_recordas(db, user_id),
        followers=count_followers(db, user_id),
        following=count_following(db, user_id),
    )


def _build_favorite_song(user: AppUser) -> ProfileFavoriteSong:
    if (
        user.fav_song_deezer_track_id is None
        or user.fav_song_title is None
        or user.fav_song_artist_name is None
        or user.fav_song_cover_url is None
    ):
        raise IncompleteProfileError
    return ProfileFavoriteSong(
        deezer_track_id=user.fav_song_deezer_track_id,
        title=user.fav_song_title,
        artist_name=user.fav_song_artist_name,
        cover_url=user.fav_song_cover_url,
        preview_url=public_preview_url(
            user.fav_song_deezer_track_id, user.fav_song_preview_url
        ),
    )
