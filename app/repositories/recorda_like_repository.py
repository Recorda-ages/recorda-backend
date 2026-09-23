"""Persistence helpers for likes on Recordas."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.recorda_like import RecordaLike


def create_if_absent(db: Session, *, user_id: UUID, recorda_id: UUID) -> bool:
    """Insert a like once and return whether a new row was created."""
    dialect = db.bind.dialect.name if db.bind is not None else ""

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError(f"Unsupported database dialect for likes: {dialect}")

    statement = (
        insert(RecordaLike)
        .values(user_id=user_id, recorda_id=recorda_id)
        .on_conflict_do_nothing(index_elements=["user_id", "recorda_id"])
        .returning(RecordaLike.user_id)
    )
    return db.execute(statement).scalar_one_or_none() is not None


def delete_for_user(db: Session, *, user_id: UUID, recorda_id: UUID) -> bool:
    statement = delete(RecordaLike).where(
        RecordaLike.user_id == user_id,
        RecordaLike.recorda_id == recorda_id,
    )
    return db.execute(statement).rowcount > 0


def count_for_recorda(db: Session, recorda_id: UUID) -> int:
    statement = (
        select(func.count())
        .select_from(RecordaLike)
        .where(RecordaLike.recorda_id == recorda_id)
    )
    return int(db.scalar(statement) or 0)
