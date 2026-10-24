from uuid import UUID

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda
from app.models.report import TARGET_RECORDA, TARGET_USER, Report
from app.repositories import moderation_action_repository
from app.repositories._query import only_live


def get_for_update(db: Session, user_id: UUID) -> AppUser | None:
    stmt = (
        select(AppUser)
        .where(AppUser.user_id == user_id, AppUser.deleted_at.is_(None))
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    return db.scalars(stmt).first()


def set_status(db: Session, user: AppUser, status: str) -> AppUser:
    user.status = status
    return user


def filtered_users(q: str, status: str | None):
    stmt = select(AppUser).where(AppUser.deleted_at.is_(None))
    q = q.strip()

    if q:
        try:
            user_id = UUID(q)
        except ValueError:
            escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_q}%"

            if "@" in q:
                stmt = stmt.where(AppUser.email.ilike(pattern, escape="\\"))
            else:
                stmt = stmt.where(
                    or_(
                        AppUser.name.ilike(pattern, escape="\\"),
                        AppUser.username.ilike(pattern, escape="\\"),
                        AppUser.email.ilike(pattern, escape="\\"),
                    )
                )
        else:
            stmt = stmt.where(AppUser.user_id == user_id)

    if status:
        stmt = stmt.where(AppUser.status == status)

    return stmt


def search_users(
    db: Session, *, q: str, status: str | None, limit: int, offset: int
) -> tuple[list[AppUser], int]:
    filtered = filtered_users(q=q, status=status)
    total = db.scalar(select(func.count()).select_from(filtered.subquery())) or 0
    page = (
        filtered.order_by(AppUser.username, AppUser.user_id).limit(limit).offset(offset)
    )
    return list(db.scalars(page)), total


def get_user(db: Session, user_id: UUID) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.user_id == user_id)
    return db.scalars(only_live(stmt, AppUser)).first()


def count_reports_by_user(db: Session, user_ids: list[UUID]) -> dict[UUID, int]:
    if not user_ids:
        return {}

    owner_id = func.coalesce(Report.reported_user_id, Recorda.user_id)
    rows = db.execute(
        select(owner_id, func.count(Report.report_id))
        .select_from(Report)
        .outerjoin(Recorda, Report.recorda_id == Recorda.recorda_id)
        .where(
            Report.comment_id.is_(None),
            or_(
                Report.reported_user_id.in_(user_ids),
                Recorda.user_id.in_(user_ids),
            ),
        )
        .group_by(owner_id)
    ).all()
    return dict(rows)


def count_recordas_by_user(db: Session, user_id: UUID) -> int:
    statement = select(func.count(Recorda.recorda_id)).where(
        Recorda.user_id == user_id, Recorda.deleted_at.is_(None)
    )
    return db.scalar(statement) or 0


def list_report_groups_for_user(db: Session, user_id: UUID):
    target_type = case(
        (Report.reported_user_id.is_not(None), literal(TARGET_USER)),
        else_=literal(TARGET_RECORDA),
    )
    target_id = func.coalesce(Report.reported_user_id, Report.recorda_id)
    return list(
        db.execute(
            select(
                target_type.label("target_type"),
                target_id.label("target_id"),
                Report.status.label("status"),
                func.count(Report.report_id).label("report_count"),
                func.min(Report.created_at).label("first_reported_at"),
                func.max(Report.created_at).label("last_reported_at"),
            )
            .select_from(Report)
            .outerjoin(Recorda, Report.recorda_id == Recorda.recorda_id)
            .where(
                Report.comment_id.is_(None),
                or_(
                    Report.reported_user_id == user_id,
                    Recorda.user_id == user_id,
                ),
            )
            .group_by(Report.reported_user_id, Report.recorda_id, Report.status)
            .order_by(target_type, target_id, Report.status)
        ).all()
    )


def list_actions_for_user(db: Session, user_id: UUID):
    return moderation_action_repository.list_for_target(
        db, target_type="USER", target_id=user_id
    )
