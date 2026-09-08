"""Business logic and orchestration for the Recorda entity."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Recorda
from app.repositories import recorda_repository
from app.schemas.recorda import RecordaCreate, RecordaUpdate


def get_all(db: Session) -> list[Recorda]:
    return recorda_repository.get_all(db)


def get_by_id(db: Session, recorda_id: int) -> Recorda | None:
    return recorda_repository.get_by_id(db, recorda_id)


def create(db: Session, payload: RecordaCreate) -> Recorda:
    now = datetime.today()
    recorda = Recorda(
        midia=payload.midia,
        music=payload.music,
        description=payload.description,
        data=now.strftime("%d/%m/%Y"),
    )
    return recorda_repository.create(db, recorda)


def update(db: Session, recorda_id: int, payload: RecordaUpdate) -> Recorda | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return None
    if payload.midia is not None:
        recorda.midia = payload.midia
    if payload.music is not None:
        recorda.music = payload.music
    if payload.description is not None:
        recorda.description = payload.description
    if payload.data is not None:
        recorda.data = payload.data
    return recorda_repository.save(db, recorda)


def delete(db: Session, recorda_id: int) -> bool:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return False
    recorda_repository.delete(db, recorda)
    return True
