"""Business logic for the administrative removal of reported Recordas."""

from typing import Any, Protocol
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.app_user import AppUser
from app.models.moderation_action import ACTION_REMOVE_RECORDA, ModerationAction
from app.models.report import STATUS_RESOLVED, TARGET_RECORDA
from app.repositories import recorda_repository
from app.schemas.admin_recorda_moderation import (
    RemoveRecordaRequest,
    RemoveRecordaResponse,
)
from app.services import recorda_service

NOT_FOUND_MESSAGE = "Recorda não encontrada."
ALREADY_REMOVED_MESSAGE = "Esta Recorda já foi removida."


class ResolveOpenReports(Protocol):
    def __call__(
        self, db: Session, *, target_type: str, target_id: UUID, new_status: str
    ) -> int: ...


class RecordAction(Protocol):
    def __call__(
        self,
        db: Session,
        *,
        admin: AppUser,
        action_type: str,
        reason: str,
        target_user_id: UUID | None = None,
        target_recorda_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> ModerationAction: ...


def remove_recorda(
    db: Session,
    recorda_id: UUID,
    payload: RemoveRecordaRequest,
    current_admin: AppUser,
    *,
    resolve_reports: ResolveOpenReports,
    record_action: RecordAction,
) -> RemoveRecordaResponse:
    try:
        recorda = recorda_repository.get_by_id_including_deleted(db, recorda_id)
        if recorda is None:
            raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
        if recorda.deleted_at is not None:
            raise HTTPException(status_code=409, detail=ALREADY_REMOVED_MESSAGE)

        recorda_service.soft_delete_with_cleanup(db, recorda, commit=False)
        resolved_reports = resolve_reports(
            db,
            target_type=TARGET_RECORDA,
            target_id=recorda_id,
            new_status=STATUS_RESOLVED,
        )
        record_action(
            db,
            admin=current_admin,
            action_type=ACTION_REMOVE_RECORDA,
            target_recorda_id=recorda_id,
            target_user_id=recorda.user_id,
            reason=payload.reason,
            details={"resolved_reports": resolved_reports},
        )
        # US 42 (Won't): notification_service.notify_content_removed(db, recorda)
        removed_at = recorda.deleted_at
        db.commit()
        return RemoveRecordaResponse(
            recorda_id=recorda_id,
            deleted_at=removed_at,
            resolved_reports=resolved_reports,
        )
    except Exception:
        db.rollback()
        raise
