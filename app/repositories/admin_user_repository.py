from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda
from app.models.report import Report
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
            escaped_q = q.replace("%", "\\%").replace("_", "\\_").replace("\\", "\\\\")
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

    return dict(
        db.execute(
            select(Report.reported_user_id, func.count())
            .where(Report.reported_user_id.in_(user_ids))
            .group_by(Report.reported_user_id)
        ).all()
    )


def count_recordas_by_user(db: Session, user_id: UUID) -> int:
    statement = select(func.count(Recorda.recorda_id)).where(
        Recorda.user_id == user_id, Recorda.deleted_at.is_(None)
    )
    return db.scalar(statement) or 0


def list_report_groups_for_user(db: Session, user_id: UUID):
    return list(
        db.execute(
            select(
                Report.status,
                func.count(Report.report_id).label("report_count"),
                func.min(Report.created_at).label("first_reported_at"),
                func.max(Report.created_at).label("last_reported_at"),
            )
            .where(
                Report.reported_user_id == user_id,
                Report.comment_id.is_(None),
            )
            .group_by(Report.status)
            .order_by(Report.status)
        ).all()
    )


def list_actions_for_user(db: Session, user_id: UUID):
    return moderation_action_repository.list_for_target(
        db, target_type="USER", target_id=user_id
    )


def to_admin_user_row(user: AppUser, reports_count: int) -> dict[str, object]:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "profile_picture_url": user.profile_picture_url,
        "role": user.role,
        "status": user.status,
        "reports_count": reports_count,
    }
