"""Persistence access for moderation reports."""

from typing import Literal
from uuid import UUID

from sqlalchemy import Row, Select, case, exists, func, literal, select
from sqlalchemy.orm import Session

from app.models.report import TARGET_RECORDA, TARGET_USER, Report

GroupOrder = Literal["desc", "asc"]


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


def list_groups(
    db: Session,
    *,
    target_type: str | None,
    status: str,
    order: GroupOrder,
    limit: int,
    offset: int,
) -> list[Row]:
    query = _grouped(target_type=target_type, status=status)
    last_reported_at = query.selected_columns.last_reported_at
    target_id = query.selected_columns.target_id

    if order == "asc":
        query = query.order_by(last_reported_at.asc(), target_id.asc())
    else:
        query = query.order_by(last_reported_at.desc(), target_id.desc())

    return list(db.execute(query.limit(limit).offset(offset)).all())


def count_groups(db: Session, *, target_type: str | None, status: str) -> int:
    grouped = _grouped(target_type=target_type, status=status).subquery()
    return db.execute(select(func.count()).select_from(grouped)).scalar_one()


def _grouped(*, target_type: str | None, status: str) -> Select:
    query = (
        select(
            case(
                (Report.recorda_id.is_not(None), literal(TARGET_RECORDA)),
                else_=literal(TARGET_USER),
            ).label("target_type"),
            func.coalesce(Report.recorda_id, Report.reported_user_id).label(
                "target_id"
            ),
            Report.status,
            func.count().label("report_count"),
            func.min(Report.created_at).label("first_reported_at"),
            func.max(Report.created_at).label("last_reported_at"),
        )
        .where(Report.comment_id.is_(None), Report.status == status)
        .group_by(Report.recorda_id, Report.reported_user_id, Report.status)
    )

    if target_type == TARGET_RECORDA:
        query = query.where(Report.recorda_id.is_not(None))
    elif target_type == TARGET_USER:
        query = query.where(Report.reported_user_id.is_not(None))

    return query
