"""Business logic and orchestration for the Recorda entity."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.music_preview import public_preview_url
from app.models import AppUser, Recorda
from app.models.app_user import STATUS_ACTIVE
from app.repositories import (
    comment_repository,
    follow_repository,
    recorda_like_repository,
    recorda_repository,
    user_repository,
)
from app.schemas.recorda import (
    RecordaAuthor,
    RecordaCreate,
    RecordaDetail,
    RecordaUpdate,
)


class NotRecordaOwnerError(Exception):
    """Raised when a user tries to change a Recorda they did not publish."""


def get_all(db: Session) -> list[Recorda]:
    return recorda_repository.get_all(db)


def get_by_id(db: Session, recorda_id: UUID) -> Recorda | None:
    return recorda_repository.get_by_id(db, recorda_id)


def create(db: Session, payload: RecordaCreate, author: AppUser) -> Recorda:
    recorda = Recorda(user_id=author.user_id, **payload.model_dump())
    return recorda_repository.create(db, recorda)


def update(
    db: Session, recorda_id: UUID, payload: RecordaUpdate, author: AppUser
) -> Recorda | None:
    recorda = _get_owned(db, recorda_id, author)
    if recorda is None:
        return None
    if payload.description is not None:
        recorda.description = payload.description
    return recorda_repository.save(db, recorda)


def delete(db: Session, recorda_id: UUID, author: AppUser) -> bool:
    recorda = _get_owned(db, recorda_id, author)
    if recorda is None:
        return False
    recorda_like_repository.delete_all_for_recorda(db, recorda_id)
    comment_repository.soft_delete_all_for_recorda(db, recorda_id)
    recorda_repository.soft_delete(db, recorda)
    return True


def _get_owned(db: Session, recorda_id: UUID, author: AppUser) -> Recorda | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is not None and recorda.user_id != author.user_id:
        raise NotRecordaOwnerError
    return recorda


class RecordaAccessDeniedError(Exception):
    """Raised when a user tries to access a Recorda they are not allowed to."""


def get_by_id_for_viewer(
    db: Session, recorda_id: UUID, viewer: AppUser
) -> RecordaDetail | None:
    """GET /recordas/{id} respeitando privacidade.

    Regras: 1) o autor sempre acessa;
            2) conta pública é visível pra qualquer usuário autenticado;
            3) conta privada só é visível pro próprio autor ou por um seguidor com vínculo ACCEPTED.
    """
    recorda = get_viewable_recorda(db, recorda_id, viewer)
    if recorda is None:
        return None

    author = user_repository.get_by_id(db, recorda.user_id)

    likes_count = recorda_like_repository.count_for_recorda(db, recorda.recorda_id)
    is_liked = recorda_like_repository.is_liked_by_user(
        db,
        user_id=viewer.user_id,
        recorda_id=recorda.recorda_id,
    )

    return RecordaDetail(
        recorda_id=recorda.recorda_id,
        author=RecordaAuthor(
            user_id=author.user_id,
            username=author.username,
            avatar_url=author.profile_picture_url,
        ),
        media_url=recorda.media_url,
        media_type=recorda.media_type,
        description=recorda.description,
        deezer_track_id=recorda.deezer_track_id,
        song_title=recorda.song_title,
        song_artist_name=recorda.song_artist_name,
        song_cover_url=recorda.song_cover_url,
        song_preview_url=public_preview_url(
            recorda.deezer_track_id, recorda.song_preview_url
        ),
        created_at=recorda.created_at,
        is_liked=is_liked,
        likes_count=likes_count,
    )


def get_viewable_recorda(
    db: Session, recorda_id: UUID, viewer: AppUser
) -> Recorda | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return None

    author = user_repository.get_by_id(db, recorda.user_id)
    if author is None or author.status != STATUS_ACTIVE:
        return None

    if author.user_id != viewer.user_id and author.is_private:
        if not follow_repository.is_accepted_follower(
            db, viewer.user_id, author.user_id
        ):
            raise RecordaAccessDeniedError
    return recorda
