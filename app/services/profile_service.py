"""Montagem do cabeçalho do perfil (contrato ProfileRead, C-2 do Épico 06)."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.core.music_preview import public_preview_url
from app.core.time import now_utc, to_local
from app.models import AppUser
from app.repositories import follow_repository, recorda_repository
from app.schemas.profile import (
    ProfileCounts,
    ProfileFavoriteSong,
    ProfileRead,
    ProfileRelationship,
    ProfileStreak,
)
from sqlalchemy.orm import Session


class IncompleteProfileError(Exception):
    """O usuário ainda não concluiu o onboarding musical."""


def count_recordas(db: Session, user_id: UUID) -> int:
    """Recordas vivas: exclusões pelo autor e pela moderação não contam."""
    return recorda_repository.count_by_user(db, user_id)


def count_followers(db: Session, user_id: UUID) -> int:
    return follow_repository.count_followers(db, user_id)


def count_following(db: Session, user_id: UUID) -> int:
    return follow_repository.count_following(db, user_id)


def calculate_streak(days: set[date], today: date) -> ProfileStreak:
    """Dias seguidos com ao menos uma Recorda publicada, terminando hoje ou ontem.

    Hoje ainda não terminou: sem publicação hoje, a sequência de ontem segue valendo.
    """
    published_today = today in days
    day = today if published_today else today - timedelta(days=1)

    current_days = 0
    while day in days:
        current_days += 1
        day -= timedelta(days=1)

    return ProfileStreak(current_days=current_days, published_today=published_today)


def build_streak(db: Session, user_id: UUID) -> ProfileStreak:
    """Inclui Recordas excluídas: o dia conquistado não se perde (US35)."""
    days = {
        _to_publication_day(created_at)
        for created_at in recorda_repository.list_publication_times(db, user_id)
    }
    return calculate_streak(days, to_local(now_utc()).date())


def _to_publication_day(value: datetime) -> date:
    """Dia de calendário em America/Sao_Paulo.

    O SQLite dos testes devolve datetime sem fuso; o valor gravado é UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return to_local(value).date()


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
        streak=build_streak(db, owner.user_id),
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