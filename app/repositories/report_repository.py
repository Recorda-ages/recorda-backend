"""Persistence access for moderation reports."""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.report import Report


def add(db: Session, report: Report) -> Report:
    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def exists_for_recorda(db: Session, *, reporter_id: UUID, recorda_id: UUID) -> bool:
    statement = select(
        exists().where(
            Report.reporter_id == reporter_id,
            Report.recorda_id == recorda_id,
        )
    )
    return bool(db.scalar(statement))


def exists_for_user(db: Session, *, reporter_id: UUID, reported_user_id: UUID) -> bool:
    statement = select(
        exists().where(
            Report.reporter_id == reporter_id,
            Report.reported_user_id == reported_user_id,
        )
    )
    return bool(db.scalar(statement))
