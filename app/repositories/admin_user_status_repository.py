from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppUser


def get_for_update(db: Session, user_id: UUID) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.user_id == user_id).with_for_update()
    return db.scalars(stmt).first()


def set_status(db: Session, user: AppUser, status: str) -> AppUser:
    user.status = status
    db.flush()
    return user
