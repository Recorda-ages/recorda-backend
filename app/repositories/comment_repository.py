"""Persistence access for Recorda comments."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import delete as delete_stmt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AppUser, Notification, RecordaComment
from app.repositories._query import only_active_users, only_live


def get_by_id(db: Session, comment_id: UUID) -> RecordaComment | None:
    stmt = select(RecordaComment).where(RecordaComment.comment_id == comment_id)
    return db.scalars(only_live(stmt, RecordaComment)).first()


def list_for_recorda(db: Session, recorda_id: UUID):
    stmt = (
        select(RecordaComment, AppUser.username, AppUser.profile_picture_url)
        .join(AppUser, AppUser.user_id == RecordaComment.user_id)
        .where(
            RecordaComment.recorda_id == recorda_id,
            RecordaComment.deleted_at.is_(None),
        )
        .order_by(RecordaComment.created_at, RecordaComment.comment_id)
    )
    return db.execute(only_active_users(stmt)).all()


def count_visible_for_recordas(
    db: Session, recorda_ids: Collection[UUID]
) -> dict[UUID, int]:
    """Contagens em lote com a mesma visibilidade da listagem de comentários."""
    stmt = (
        select(RecordaComment.recorda_id, func.count())
        .join(AppUser, AppUser.user_id == RecordaComment.user_id)
        .where(RecordaComment.recorda_id.in_(recorda_ids))
        .group_by(RecordaComment.recorda_id)
    )
    return dict(db.execute(only_active_users(only_live(stmt, RecordaComment))).all())


def delete(db: Session, comment: RecordaComment) -> None:
    db.execute(
        delete_stmt(Notification).where(Notification.comment_id == comment.comment_id)
    )
    db.delete(comment)
    db.commit()


def delete_all_for_recorda(db: Session, recorda_id: UUID) -> None:
    db.execute(
        delete_stmt(RecordaComment).where(RecordaComment.recorda_id == recorda_id)
    )
