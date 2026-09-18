"""Business logic and orchestration for the Recorda entity."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AppUser, Recorda
from app.repositories import recorda_repository
from app.schemas.recorda import RecordaCreate, RecordaUpdate


class NotRecordaOwnerError(Exception):
    """Raised when a user tries to change a Recorda they did not publish."""


def get_all(db: Session) -> list[Recorda]:
    return recorda_repository.get_all(db)


def get_by_id(db: Session, recorda_id: UUID) -> Recorda | None:
    return recorda_repository.get_by_id(db, recorda_id)


def create(db: Session, payload: RecordaCreate, author: AppUser) -> Recorda:
    recorda = Recorda(user_id=author.user_id, **payload.model_dump())
    return recorda_repository.create(db, recorda)


def update(
    db: Session, recorda_id: UUID, payload: RecordaUpdate, author: AppUser
) -> Recorda | None:
    recorda = _get_owned(db, recorda_id, author)
    if recorda is None:
        return None
    if payload.description is not None:
        recorda.description = payload.description
    return recorda_repository.save(db, recorda)


def delete(db: Session, recorda_id: UUID, author: AppUser) -> bool:
    recorda = _get_owned(db, recorda_id, author)
    if recorda is None:
        return False
    recorda_repository.soft_delete(db, recorda)
    return True


def _get_owned(db: Session, recorda_id: UUID, author: AppUser) -> Recorda | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is not None and recorda.user_id != author.user_id:
        raise NotRecordaOwnerError
    return recorda
