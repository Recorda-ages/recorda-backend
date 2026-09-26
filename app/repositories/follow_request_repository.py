from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.follow import Follow


def get_for_update(db: Session, follow_id: UUID) -> Follow | None:
    stmt = select(Follow).where(Follow.follow_id == follow_id).with_for_update()
    return db.scalars(stmt).first()


def delete(db: Session, follow: Follow) -> None:
    db.delete(follow)
