from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recorda


def search_retrospectives(db: Session, user_id: UUID) -> list[datetime]:
    stmt = select(Recorda.created_at).where(
        Recorda.user_id == user_id,
        Recorda.deleted_at.is_(None),
    )
    return list(db.scalars(stmt))
