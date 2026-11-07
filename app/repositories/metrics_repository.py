"""Only live publications belonging to the authenticated account."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recorda


def list_recordas(
    db: Session, user_id: UUID, start: datetime | None, end: datetime
) -> tuple[Recorda, ...]:
    query = select(Recorda).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
        Recorda.created_at <= end,
    )
    if start is not None:
        query = query.where(Recorda.created_at >= start)
    return tuple(db.scalars(query.order_by(Recorda.created_at, Recorda.recorda_id)))


def list_publication_times(db: Session, user_id: UUID, end: datetime) -> list[datetime]:
    return list(
        db.scalars(
            select(Recorda.created_at).where(
                Recorda.user_id == user_id,
                Recorda.deleted_at.is_(None),
                Recorda.created_at <= end,
            )
        )
    )
