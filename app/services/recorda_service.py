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
    recorda = Recorda(midia=payload.midia, music=payload.music, description=payload.description, data=payload.data)
    if payload.midia is None or payload.music is None or len(payload.midia) < 1 or len(payload.music) < 1:
        raise ValueError("Music and Midia must be provided for creating a Recorda.")
    if len(payload.description) > 2200:
        raise ValueError("The 'description' field must not exceed 2200 characters.")
    now = datetime.today()
    data_str = now.strftime("%d/%m/%Y")
    recorda.data = data_str
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
