"""Persistence and query access for the Recorda entity."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import Recorda
from app.repositories._query import only_live


def get_all(db: Session) -> list[Recorda]:
    stmt = only_live(select(Recorda), Recorda).order_by(Recorda.created_at.desc())
    return list(db.scalars(stmt))


def get_by_id(db: Session, recorda_id: UUID) -> Recorda | None:
    stmt = select(Recorda).where(Recorda.recorda_id == recorda_id)
    return db.scalars(only_live(stmt, Recorda)).first()


def list_by_user(db: Session, user_id: UUID) -> list[Recorda]:
    stmt = (
        select(Recorda)
        .where(Recorda.user_id == user_id)
        .order_by(Recorda.created_at.desc())
    )
    return list(db.scalars(only_live(stmt, Recorda)))


def create(db: Session, recorda: Recorda) -> Recorda:
    db.add(recorda)
    db.commit()
    db.refresh(recorda)
    return recorda


def save(db: Session, recorda: Recorda) -> Recorda:
    db.commit()
    db.refresh(recorda)
    return recorda


def soft_delete(db: Session, recorda: Recorda) -> None:
    recorda.deleted_at = now_utc()
    db.commit()
