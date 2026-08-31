"""Persistence and query access for the Recorda entity."""

from sqlalchemy.orm import Session

from app.models import Recorda


def get_all(db: Session) -> list[Recorda]:
    return db.query(Recorda).all()


def get_by_id(db: Session, recorda_id: int) -> Recorda | None:
    return db.get(Recorda, recorda_id)


def get_by_midia(db: Session, midia: str) -> Recorda | None:
    return db.query(Recorda).filter_by(midia=midia).first()


def get_by_music(db: Session, music: str) -> Recorda | None:
    return db.query(Recorda).filter_by(music=music).first()


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
