"""Business logic and orchestration for the Recorda entity."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Recorda, User
from app.repositories import recorda_repository
from app.schemas.recorda import RecordaCreate, RecordaUpdate


def get_all(db: Session) -> list[Recorda]:
    return recorda_repository.get_all(db)


def get_by_id(db: Session, recorda_id: int) -> Recorda | None:
    return recorda_repository.get_by_id(db, recorda_id)


def create(db: Session, payload: RecordaCreate, author: User) -> Recorda:
    now = datetime.today()
    recorda = Recorda(
        user_id=author.id,
        midia=payload.midia,
        media_type=payload.media_type,
        music=payload.music,
        deezer_track_id=payload.deezer_track_id,
        song_artist_name=payload.song_artist_name,
        song_cover_url=payload.song_cover_url,
        description=payload.description,
        data=now.strftime("%d/%m/%Y"),
    )
    return recorda_repository.create(db, recorda)


def update(db: Session, recorda_id: int, payload: RecordaUpdate) -> Recorda | None:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return None
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(recorda, field, value)
    return recorda_repository.save(db, recorda)


def delete(db: Session, recorda_id: int) -> bool:
    recorda = recorda_repository.get_by_id(db, recorda_id)
    if recorda is None:
        return False
    recorda_repository.delete(db, recorda)
    return True
