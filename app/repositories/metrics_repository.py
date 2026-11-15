"""Only live publications belonging to the authenticated account."""

from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recorda
from app.schemas.metrics import RecordaMetrics


def list_recordas(
    db: Session, user_id: UUID, start: datetime | None, end: datetime
) -> tuple[RecordaMetrics, ...]:
    query = select(
        Recorda.recorda_id,
        Recorda.created_at,
        Recorda.song_artist_name,
        Recorda.song_cover_url,
        Recorda.song_genre_name,
    ).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
        Recorda.created_at <= end,
    )
    if start is not None:
        query = query.where(Recorda.created_at >= start)
    return tuple(
        RecordaMetrics(*row)
        for row in db.execute(query.execution_options(yield_per=1000))
    )


def iter_publication_times(
    db: Session, user_id: UUID, end: datetime
) -> Iterator[datetime]:
    """Stream historical timestamps without materializing duplicate post dates."""
    query = select(Recorda.created_at).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
        Recorda.created_at <= end,
    )
    yield from db.scalars(query.execution_options(yield_per=1000))
