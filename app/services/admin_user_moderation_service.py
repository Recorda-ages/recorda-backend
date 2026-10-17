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
from app.schemas.admin_user import AdminUserPage
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
    # if user isn't an admin, they shouldn't be able to access this endpoint
    if not users.id == ROLE_ADMIN:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this resource."
        )
    users, total = admin_user_repository.search_users(
        db, q=q, status=status, limit=limit, offset=offset
    )
    if limit == 0 or limit is None or limit > 50:
        raise HTTPException(
            status_code=422,
            detail={"limit": "Limit must be between 1 and 50."},
        )
    if offset < 0 or offset is None:
        raise HTTPException(
            status_code=422,
            detail={"offset": "Offset must be greater than or equal to 0."},
        )
    if status is not None and status not in [STATUS_ACTIVE, STATUS_SUSPENDED]:
        raise HTTPException(
            status_code=422,
            detail={"status": "Status must be either 'ACTIVE' or 'SUSPENDED'."},
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

def get_user(db: Session, *, user_id: UUID) -> AdminUserPage:
    user = admin_user_repository.get_for_update(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found."
        )
    report_count = admin_user_repository.count_reports_by_user(db, [user.user_id]).get(user.user_id, 0)
    item = admin_user_repository.to_admin_user_row(user, report_count)
    return AdminUserPage(items=[item], total=1)