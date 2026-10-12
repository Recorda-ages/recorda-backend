from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models import AppUser
from app.repositories import report_repository
from app.schemas.admin_user_moderation import (
    ReactivateUserRequest,
    SuspendUserRequest,
    UserStatusResponse,
)
from app.services import (
    admin_user_moderation_service,
    moderation_service,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_current_admin = Depends(get_current_admin_user)


@router.post("/{user_id}/suspend", status_code=status.HTTP_200_OK)
def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Response:
    admin_user_moderation_service.suspend_user(
        db,
        user_id,
        payload,
        current_admin,
        resolve_reports=report_repository.resolve_open_user_reports,
        record_action=moderation_service.record_action,
    )
    return UserStatusResponse(status_code=200, user_id=user_id, status="SUSPENDED")


@router.post("/{user_id}/reactivate", status_code=status.HTTP_200_OK)
def reactivate_user(
    user_id: UUID,
    payload: ReactivateUserRequest,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Response:
    admin_user_moderation_service.reactivate_user(
        db,
        user_id,
        payload,
        current_admin,
        record_action=moderation_service.record_action,
    )
    return UserStatusResponse(status_code=200, user_id=user_id, status="REACTIVATED")
