from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models import Recorda, RecordaComment, RecordaLike


def search_retrospectives(db: Session, user_id: UUID) -> list[datetime]:
    stmt = select(Recorda.created_at).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
    )
    return list(db.scalars(stmt))


def _live_recordas_in_period(
    user_id: UUID, start: datetime, end: datetime
) -> tuple[ColumnElement[bool], ...]:
    """Recordas vivas do usuário em [start, end), mesmo recorte das métricas."""
    return (
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
        Recorda.created_at >= start,
        Recorda.created_at < end,
    )


def count_likes_received(
    db: Session, user_id: UUID, start: datetime, end: datetime
) -> int:
    """Curtidas recebidas pelas Recordas publicadas no período."""
    stmt = (
        select(func.count())
        .select_from(RecordaLike)
        .join(Recorda, Recorda.recorda_id == RecordaLike.recorda_id)
        .where(*_live_recordas_in_period(user_id, start, end))
    )
    return int(db.scalar(stmt) or 0)


def count_comments_received(
    db: Session, user_id: UUID, start: datetime, end: datetime
) -> int:
    """Comentários vivos recebidos pelas Recordas publicadas no período."""
    stmt = (
        select(func.count())
        .select_from(RecordaComment)
        .join(Recorda, Recorda.recorda_id == RecordaComment.recorda_id)
        .where(
            *_live_recordas_in_period(user_id, start, end),
            RecordaComment.deleted_at.is_(None),
        )
    )
    return int(db.scalar(stmt) or 0)
