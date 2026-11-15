"""Business logic and orchestration for the Recorda entity."""

from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import delete as delete_stmt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.music_preview import public_preview_url
from app.models import AppUser, Notification, Recorda, RecordaComment, RecordaMention
from app.models.app_user import STATUS_ACTIVE
from app.models.notification import TYPE_MENTION
from app.repositories import (
    comment_repository,
    follow_repository,
    recorda_like_repository,
    recorda_repository,
    user_repository,
)
from app.repositories._query import only_active_users
from app.schemas.recorda import (
    RecordaAuthor,
    RecordaCreate,
    RecordaDetail,
    RecordaUpdate,
)
from app.services import music_service, profile_service


class NotRecordaOwnerError(Exception):
    """Raised when a user tries to change a Recorda they did not publish."""


def list_visible_to_user(db: Session, viewer: AppUser) -> list[Recorda]:
    return recorda_repository.list_visible_to_user(db, viewer)


def get_by_id(db: Session, recorda_id: UUID) -> Recorda | None:
    return recorda_repository.get_by_id(db, recorda_id)


def create(
    db: Session, payload: RecordaCreate, author: AppUser, deezer: httpx.Client
) -> Recorda:
    # ASVS 2.2.1, 8.3.1: validate targets and publication visibility on the server.
    mentioned_ids = set(payload.mentioned_user_ids)
    mentioned = list(
        db.scalars(
            only_active_users(select(AppUser).where(AppUser.user_id.in_(mentioned_ids)))
        )
    )
    if len(mentioned) != len(mentioned_ids) or any(
        user.user_id == author.user_id
        or not follow_repository.is_accepted_follower(db, author.user_id, user.user_id)
        or not profile_service.can_view_content(db, author, user)
        for user in mentioned
    ):
        raise HTTPException(
            status_code=422,
            detail="Marque apenas amigos ativos que podem ver esta Recorda.",
        )
    values = payload.model_dump(exclude={"mentioned_user_ids"})
    if not values["song_genre_name"] or not values["song_genre_name"].strip():
        values["song_genre_name"] = music_service.get_track_genre_name(
            deezer, payload.deezer_track_id
        )
    recorda = Recorda(user_id=author.user_id, **values)
    db.add(recorda)
    db.flush()
    for user in mentioned:
        db.add(RecordaMention(recorda_id=recorda.recorda_id, user_id=user.user_id))
        db.add(
            Notification(
                recipient_id=user.user_id,
                sender_id=author.user_id,
                recorda_id=recorda.recorda_id,
                type=TYPE_MENTION,
            )
        )
    db.commit()
    db.refresh(recorda)
    return recorda


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
    delete_with_cleanup(db, recorda)
    return True


def delete_with_cleanup(db: Session, recorda: Recorda, *, commit: bool = True) -> None:
    """Remove conteúdo e notificações; mantém IDs nas denúncias e na auditoria."""
    # ASVS 1.2.4: cleanup uses bound ORM predicates within the caller's transaction.
    comment_ids = select(RecordaComment.comment_id).where(
        RecordaComment.recorda_id == recorda.recorda_id
    )
    db.execute(
        delete_stmt(Notification).where(
            (Notification.recorda_id == recorda.recorda_id)
            | Notification.comment_id.in_(comment_ids)
        )
    )
    recorda_like_repository.delete_all_for_recorda(db, recorda.recorda_id)
    comment_repository.delete_all_for_recorda(db, recorda.recorda_id)
    recorda_repository.delete(db, recorda, commit=commit)


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
        song_genre_name=recorda.song_genre_name,
        created_at=recorda.created_at,
        is_liked=is_liked,
        likes_count=likes_count,
        mentioned_users=[
            RecordaAuthor(
                user_id=user.user_id,
                username=user.username,
                avatar_url=user.profile_picture_url,
            )
            for user in db.scalars(
                only_active_users(
                    select(AppUser)
                    .join(RecordaMention, RecordaMention.user_id == AppUser.user_id)
                    .where(RecordaMention.recorda_id == recorda_id)
                    .order_by(AppUser.username)
                )
            )
        ],
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

    if not profile_service.can_view_content(db, author, viewer):
        raise RecordaAccessDeniedError
    return recorda
