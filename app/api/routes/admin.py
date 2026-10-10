"""Router administrativo /admin com a guarda de admin aplicada no router (T-E10.BE.01)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.repositories.report_repository import GroupOrder
from app.schemas.moderation import AdminSummary, AuditLogPage, ModerationActionType
from app.schemas.report import ReportGroupPage, ReportStatus, ReportTargetType
from app.services import admin_report_service, moderation_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)

INVALID_PERIOD_MESSAGE = "A data inicial não pode ser posterior à data final."


@router.get("/reports", response_model=ReportGroupPage)
def list_report_groups(
    target_type: ReportTargetType | None = None,
    status: ReportStatus = "OPEN",
    order: GroupOrder = "desc",
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ReportGroupPage:
    """Denúncias agrupadas por alvo. Sem `status`, lista só as OPEN."""
    return admin_report_service.list_groups(
        db,
        target_type=target_type,
        status=status,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-log", response_model=AuditLogPage)
def list_audit_log(
    admin_id: UUID | None = None,
    action_type: ModerationActionType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    """Trilha de auditoria somente leitura. Datas inclusivas no fuso de São Paulo."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail={
                "message": INVALID_PERIOD_MESSAGE,
                "fields": [{"field": "date_from", "message": INVALID_PERIOD_MESSAGE}],
            },
        )

    return moderation_service.list_audit_log(
        db,
        admin_id=admin_id,
        action_type=action_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/admins", response_model=list[AdminSummary])
def list_admins(db: Session = Depends(get_db)) -> list[AdminSummary]:
    """Contas administrativas, para popular o filtro do log de auditoria."""
    return moderation_service.list_admins(db)
