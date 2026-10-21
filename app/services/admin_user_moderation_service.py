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
        admin_user_repository.to_admin_user_row(
            user, report_counts.get(user.user_id, 0)
        )
        for user in users
    ]
    return AdminUserPage(items=items, total=total)


def get_user(db: Session, *, user_id: UUID) -> AdminUserDetail:
    user = admin_user_repository.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found."
        )

    row = admin_user_repository.to_admin_user_row(
        user,
        admin_user_repository.count_reports_by_user(db, [user_id]).get(user_id, 0),
    )
    reports_received = [
        AdminUserReportGroup(
            target_type="USER",
            target_id=user_id,
            status=report.status,
            report_count=report.report_count,
            first_reported_at=report.first_reported_at,
            last_reported_at=report.last_reported_at,
        )
        for report in admin_user_repository.list_report_groups_for_user(db, user_id)
    ]
    actions = [
        AdminUserAction(
            action_id=action.action_id,
            action_type=action.action_type,
            admin_id=action.admin_id,
            admin_username=admin_username,
            target_user_id=action.target_user_id,
            target_recorda_id=action.target_recorda_id,
            reason=action.reason,
            details=action.details,
            created_at=action.created_at,
        )
        for action, admin_username, _, _ in admin_user_repository.list_actions_for_user(
            db, user_id
        )
    ]
    return AdminUserDetail(
        **row,
        created_at=user.created_at,
        is_private=user.is_private,
        recordas_count=admin_user_repository.count_recordas_by_user(db, user_id),
        reports_received=reports_received,
        actions=actions,
    )
