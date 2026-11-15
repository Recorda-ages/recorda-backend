"""Business logic for suspending and reactivating user accounts."""

from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.app_user import ROLE_ADMIN, STATUS_ACTIVE, STATUS_SUSPENDED, AppUser
from app.models.moderation_action import (
    ACTION_REACTIVATE_USER,
    ACTION_SUSPEND_USER,
    ModerationAction,
)
from app.repositories import admin_user_repository
from app.repositories.admin_user_repository import get_for_update, set_status
from app.schemas.admin_user import (
    AdminUserAction,
    AdminUserDetail,
    AdminUserPage,
    AdminUserReportGroup,
)
from app.schemas.admin_user_moderation import ReactivateUserRequest, SuspendUserRequest
from app.services.report_preview_service import load_target_previews

ResolveReports = Callable[[Session, UUID], int]


class RecordAction(Protocol):
    def __call__(
        self,
        db: Session,
        *,
        admin: AppUser,
        action_type: str,
        target_user_id: UUID,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> ModerationAction: ...


def suspend_user(
    db: Session,
    user_id: UUID,
    payload: SuspendUserRequest,
    current_admin: AppUser,
    *,
    resolve_reports: ResolveReports,
    record_action: RecordAction,
) -> AppUser:
    try:
        user = get_for_update(db, user_id)
        if user is None:
            raise HTTPException(
                status_code=404, detail=f"User with ID {user_id} not found."
            )
        if user.user_id == current_admin.user_id:
            raise HTTPException(status_code=400, detail="You cannot suspend yourself.")
        if user.role == ROLE_ADMIN:
            raise HTTPException(
                status_code=403, detail="You cannot suspend another admin user."
            )
        if user.status == STATUS_SUSPENDED:
            raise HTTPException(
                status_code=409, detail=f"User with ID {user_id} is already suspended."
            )

        set_status(db, user, STATUS_SUSPENDED)
        resolved_reports = (
            resolve_reports(db, user_id) if payload.resolve_open_reports else 0
        )
        record_action(
            db,
            admin=current_admin,
            action_type=ACTION_SUSPEND_USER,
            target_user_id=user_id,
            reason=payload.reason,
            details={"resolved_reports": resolved_reports},
        )
        db.commit()
        return user
    except Exception:
        db.rollback()
        raise


def reactivate_user(
    db: Session,
    user_id: UUID,
    payload: ReactivateUserRequest,
    current_admin: AppUser,
    *,
    record_action: RecordAction,
) -> AppUser:
    try:
        user = get_for_update(db, user_id)
        if user is None:
            raise HTTPException(
                status_code=404, detail=f"User with ID {user_id} not found."
            )
        if user.status == STATUS_ACTIVE:
            raise HTTPException(
                status_code=409, detail=f"User with ID {user_id} is not suspended."
            )

        set_status(db, user, STATUS_ACTIVE)
        record_action(
            db,
            admin=current_admin,
            action_type=ACTION_REACTIVATE_USER,
            target_user_id=user_id,
            reason=payload.reason,
        )
        db.commit()
        return user
    except Exception:
        db.rollback()
        raise


def search_users(
    db: Session, *, q: str, status: str | None, limit: int, offset: int
) -> AdminUserPage:
    users, total = admin_user_repository.search_users(
        db, q=q, status=status, limit=limit, offset=offset
    )
    report_counts = admin_user_repository.count_reports_by_user(
        db, [user.user_id for user in users]
    )
    items = [
        _to_admin_user_row(user, report_counts.get(user.user_id, 0)) for user in users
    ]
    return AdminUserPage(items=items, total=total)


def get_user(db: Session, *, user_id: UUID) -> AdminUserDetail:
    user = admin_user_repository.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found."
        )

    row = _to_admin_user_row(
        user, admin_user_repository.count_reports_by_user(db, [user_id]).get(user_id, 0)
    )
    report_groups = admin_user_repository.list_report_groups_for_user(db, user_id)
    previews = load_target_previews(
        db,
        user_ids={user_id},
        recorda_ids={
            report.target_id
            for report in report_groups
            if report.target_type == "RECORDA"
        },
    )
    reports_received = [
        AdminUserReportGroup(
            target_type=report.target_type,
            target_id=report.target_id,
            status=report.status,
            report_count=report.report_count,
            first_reported_at=report.first_reported_at,
            last_reported_at=report.last_reported_at,
            preview=previews.get((report.target_type, report.target_id)),
        )
        for report in report_groups
    ]
    actions = [
        AdminUserAction(
            action_id=row.ModerationAction.action_id,
            action_type=row.ModerationAction.action_type,
            admin_id=row.ModerationAction.admin_id,
            admin_username=row.admin_username,
            target_user_id=row.ModerationAction.target_user_id,
            target_recorda_id=row.ModerationAction.target_recorda_id,
            reason=row.ModerationAction.reason,
            details=row.ModerationAction.details,
            created_at=row.ModerationAction.created_at,
        )
        # By column name: the history rows carry extra label columns.
        for row in admin_user_repository.list_actions_for_user(db, user_id)
    ]
    return AdminUserDetail(
        **row,
        created_at=user.created_at,
        is_private=user.is_private,
        recordas_count=admin_user_repository.count_recordas_by_user(db, user_id),
        reports_received=reports_received,
        actions=actions,
    )


def _to_admin_user_row(user: AppUser, reports_count: int) -> dict[str, object]:
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
