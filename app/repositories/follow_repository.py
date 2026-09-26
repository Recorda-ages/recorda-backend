


from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.follow import Follow


def get_by_id(db: Session, follow_id: UUID) -> Follow | None:
    stmt = select(Follow).where(Follow.follow_id == follow_id)
    return db.scalars(stmt).first()

def create(db: Session, follow: Follow) -> Follow:
    db.add(follow)
    db.commit()
    db.refresh(follow)
    return follow


def delete(db: Session, follow: Follow) -> None:
    db.delete(follow)
    db.commit()
