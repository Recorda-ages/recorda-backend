from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.follow import STATUS_PENDING, Follow


def get_for_update(db: Session, follow_id: UUID) -> Follow | None:
    stmt = select(Follow).where(Follow.follow_id == follow_id).with_for_update()
    return db.scalars(stmt).first()


def list_pending_for_update(db: Session, following_id: UUID) -> list[Follow]:
    stmt = (
        select(Follow)
        .where(Follow.following_id == following_id, Follow.status == STATUS_PENDING)
        .order_by(Follow.follow_id)
        .with_for_update()
    )
    return list(db.scalars(stmt))


def delete(db: Session, follow: Follow) -> None:
    db.delete(follow)
