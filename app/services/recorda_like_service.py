"""Business logic for liking and unliking Recordas."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AppUser
from app.repositories import (
    notification_repository,
    recorda_like_repository,
    recorda_repository,
)
from app.schemas.recorda import RecordaLikeState


def like(
    db: Session, *, recorda_id: UUID, current_user: AppUser
) -> RecordaLikeState | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return None

    created = recorda_like_repository.create_if_absent(
        db,
        user_id=current_user.user_id,
        recorda_id=recorda_id,
    )
    if created and recorda.user_id != current_user.user_id:
        notification_repository.create_like(
            db,
            recipient_id=recorda.user_id,
            sender_id=current_user.user_id,
            recorda_id=recorda_id,
        )

    likes_count = recorda_like_repository.count_for_recorda(db, recorda_id)
    db.commit()
    return RecordaLikeState(likes_count=likes_count, is_liked=True)


def unlike(
    db: Session, *, recorda_id: UUID, current_user: AppUser
) -> RecordaLikeState | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return None

    recorda_like_repository.delete_for_user(
        db,
        user_id=current_user.user_id,
        recorda_id=recorda_id,
    )
    likes_count = recorda_like_repository.count_for_recorda(db, recorda_id)
    db.commit()
    return RecordaLikeState(likes_count=likes_count, is_liked=False)
