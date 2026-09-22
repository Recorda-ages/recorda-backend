"""Persistence and query access for the AppUser entity."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser
from app.repositories._query import only_live
from app.models import AppUser, Follow


def get_all(db: Session) -> list[AppUser]:
    return list(db.scalars(only_live(select(AppUser), AppUser)))


def get_by_id(db: Session, user_id: UUID) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.user_id == user_id)
    return db.scalars(only_live(stmt, AppUser)).first()


def get_by_username(
    db: Session, username: str, *, include_deleted: bool = False
) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.username == username)
    if not include_deleted:
        stmt = only_live(stmt, AppUser)
    return db.scalars(stmt).first()


def get_by_email(
    db: Session, email: str, *, include_deleted: bool = False
) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.email == email)
    if not include_deleted:
        stmt = only_live(stmt, AppUser)
    return db.scalars(stmt).first()


def create(db: Session, user: AppUser) -> AppUser:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save(db: Session, user: AppUser) -> AppUser:
    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, user: AppUser) -> None:
    user.deleted_at = now_utc()
    db.commit()

def search_by_username(
    db: Session, query: str, current_user_id: UUID, limit: int = 20
) -> list[tuple[AppUser, str | None]]:

    pattern = f"%{query}%"
    stmt = (
        select(AppUser, Follow.status)
        .outerjoin(
            Follow,
            (Follow.follower_id == current_user_id)
            & (Follow.following_id == AppUser.user_id),
        )
        .where(AppUser.username.ilike(pattern))
        .where(AppUser.user_id != current_user_id)
        .order_by(AppUser.username)
        .limit(limit)
    )
    stmt = only_live(stmt, AppUser)
    return list(db.execute(stmt).all())