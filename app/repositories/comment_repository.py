"""Persistence access for Recorda comments."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import RecordaComment
from app.repositories._query import only_live


def get_by_id(db: Session, comment_id: UUID) -> RecordaComment | None:
    stmt = select(RecordaComment).where(RecordaComment.comment_id == comment_id)
    return db.scalars(only_live(stmt, RecordaComment)).first()


def soft_delete(db: Session, comment: RecordaComment) -> None:
    comment.deleted_at = now_utc()
    db.commit()
