from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda, RecordaComment, RecordaLike, RecordaMention
from app.repositories._query import only_active_users


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
        .join(AppUser, AppUser.user_id == RecordaComment.user_id)
        .join(Recorda, Recorda.recorda_id == RecordaComment.recorda_id)
        .where(
            *_live_recordas_in_period(user_id, start, end),
            RecordaComment.deleted_at.is_(None),
        )
    )
    return int(db.scalar(only_active_users(stmt)) or 0)


def top_tagged_users(db: Session, recorda_ids: list[UUID]) -> list[dict]:
    stmt = (
        select(AppUser, func.count().label("tag_count"))
        .join(RecordaMention, RecordaMention.user_id == AppUser.user_id)
        .where(RecordaMention.recorda_id.in_(recorda_ids))
        .group_by(AppUser.user_id)
        .order_by(func.count().desc(), AppUser.username)
        .limit(5)
    )
    return [
        dict(
            user_id=user.user_id,
            username=user.username,
            profile_picture_url=user.profile_picture_url,
            tag_count=count,
        )
        for user, count in db.execute(only_active_users(stmt))
    ]
