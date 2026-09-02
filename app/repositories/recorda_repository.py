"""Persistence and query access for the Recorda entity."""

from sqlalchemy.orm import Session

from app.models import Recorda


def get_all(db: Session) -> list[Recorda]:
    return db.query(Recorda).all()


def get_by_id(db: Session, recorda_id: int) -> Recorda | None:
    return db.get(Recorda, recorda_id)


def create(db: Session, recorda: Recorda) -> Recorda:
    db.add(recorda)
    db.commit()
    db.refresh(recorda)
    return recorda


def save(db: Session, recorda: Recorda) -> Recorda:
    db.commit()
    db.refresh(recorda)
    return recorda


def delete(db: Session, recorda: Recorda) -> None:
    db.delete(recorda)
    db.commit()
