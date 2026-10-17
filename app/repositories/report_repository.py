"""Persistence access for moderation reports."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import (
    Row,
    Select,
    case,
    exists,
    func,
    literal,
    select,
    update,
)

from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser
from app.models.report import (
    STATUS_OPEN,
    STATUS_RESOLVED,
    TARGET_RECORDA,
    TARGET_USER,
    Report,
)

GroupOrder = Literal["desc", "asc"]


def list_for_target(db: Session, *, target_type: str, target_id: UUID) -> list[Row]:
    """All statuses, with reporter names preserved after account deletion."""
    target_column = (
        Report.recorda_id if target_type == TARGET_RECORDA else Report.reported_user_id
    )
    statement = (
        select(
            Report,
            func.coalesce(AppUser.username, "[conta removida]").label(
                "reporter_username"
            ),
        )
        .outerjoin(AppUser, Report.reporter_id == AppUser.user_id)
        .where(target_column == target_id)
        .order_by(Report.created_at.desc(), Report.report_id.desc())
    )
    return list(db.execute(statement).all())


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


def bulk_update_status(
    db: Session,
    *,
    recorda_id: UUID | None,
    reported_user_id: UUID | None,
    from_statuses: tuple[str, ...],
    new_status: str,
    resolved_at: datetime | None,
) -> int:
    """Atualiza status de denúncias de um alvo **sem commit** (commit é do caller).

    Exatamente um de `recorda_id` ou `reported_user_id` deve ser não-nulo.
    Retorna o número de linhas afetadas.
    """
    if (recorda_id is None) == (reported_user_id is None):
        raise ValueError(
            "Exatamente um de recorda_id ou reported_user_id deve ser informado."
        )

    stmt = (
        update(Report)
        .where(Report.status.in_(from_statuses))
        .values(status=new_status, resolved_at=resolved_at)
        .execution_options(synchronize_session="fetch")
    )
    if recorda_id is not None:
        stmt = stmt.where(Report.recorda_id == recorda_id)
    else:
        stmt = stmt.where(Report.reported_user_id == reported_user_id)

    result = db.execute(stmt)
    return result.rowcount


def _grouped(*, target_type: str | None, status: str) -> Select:
    query = (
        select(
            case(
                (Report.recorda_id.is_not(None), literal(TARGET_RECORDA)),
                else_=literal(TARGET_USER),
            ).label("target_type"),
            func.func.coalesce(Report.recorda_id, Report.reported_user_id).label(
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
