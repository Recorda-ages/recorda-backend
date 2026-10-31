from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser, Recorda


def temp(db: Session, user_id: UUID) -> list[Recorda]:
    stmt = select(Recorda.created_at).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
    )
    return list(db.scalars(stmt))