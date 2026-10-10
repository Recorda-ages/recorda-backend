"""Persistence access for moderation reports."""

from uuid import UUID

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models.report import STATUS_OPEN, STATUS_RESOLVED, Report


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


def resolve_open_user_reports(db: Session, user_id: UUID) -> int:
    """Resolve open reports against a profile, without committing the session."""
    statement = (
        update(Report)
        .where(
            Report.reported_user_id == user_id,
            Report.status == STATUS_OPEN,
        )
        .values(status=STATUS_RESOLVED, resolved_at=now_utc())
        .execution_options(synchronize_session="fetch")
    )
    result = db.execute(statement)
    return int(result.rowcount or 0)
