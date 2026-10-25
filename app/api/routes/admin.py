"""Router administrativo /admin com a guarda de admin aplicada no router (T-E10.BE.01)."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.models import AppUser
from app.models.moderation_action import ACTION_CHANGE_REPORT_STATUS
from app.models.report import TARGET_RECORDA, TARGET_USER
from app.repositories import report_repository
from app.repositories.report_repository import GroupOrder
from app.schemas.admin_recorda_moderation import (
    RemoveRecordaRequest,
    RemoveRecordaResponse,
)
from app.schemas.admin_user import AdminUserDetail, AdminUserPage
from app.schemas.admin_user_moderation import (
    ReactivateUserRequest,
    SuspendUserRequest,
    UserStatusResponse,
)
from app.schemas.moderation import AdminSummary, AuditLogPage, ModerationActionType
from app.schemas.report import (
    ReportGroupDetail,
    ReportGroupPage,
    ReportStatus,
    ReportStatusChange,
    ReportStatusChanged,
    ReportTargetType,
)
from app.services import (
    admin_recorda_moderation_service,
    admin_report_service,
    admin_user_moderation_service,
    moderation_service,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)

INVALID_PERIOD_MESSAGE = "A data inicial não pode ser posterior à data final."
NO_REPORTS_TO_UPDATE_MESSAGE = "Não há denúncias neste status para alterar."


@router.get("/users", response_model=AdminUserPage)
def list_admin_users(
    q: str = Query(default=""),
    status: Literal["ACTIVE", "SUSPENDED"] | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    return admin_user_moderation_service.search_users(
        db, q=q, status=status, limit=limit, offset=offset
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_admin_user(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> AdminUserDetail:
    return admin_user_moderation_service.get_user(db, user_id=user_id)


@router.get("/reports/{target_type}/{target_id}", response_model=ReportGroupDetail)
def get_report_detail(
    target_type: ReportTargetType,
    target_id: UUID,
    db: Session = Depends(get_db),
) -> ReportGroupDetail:
    """Full reported content, including private, suspended and deleted targets."""
    try:
        return admin_report_service.get_detail(
            db, target_type=target_type, target_id=target_id
        )
    except admin_report_service.NoReportsForTargetError as exc:
        raise HTTPException(
            status_code=404, detail="Nenhuma denúncia para este alvo."
        ) from exc


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


@router.patch(
    "/reports/{target_type}/{target_id}/status",
    response_model=ReportStatusChanged,
)
def change_report_status(
    target_type: ReportTargetType,
    target_id: UUID,
    body: ReportStatusChange,
    db: Session = Depends(get_db),
    admin: AppUser = Depends(get_current_admin_user),
) -> ReportStatusChanged:
    """Muda o status em lote das denúncias de um alvo (T-E10.US44.BE.03).

    - RESOLVED / DISMISSED: afeta todas as denúncias OPEN do alvo.
    - OPEN (reabrir): afeta todas as RESOLVED/DISMISSED do alvo.
      Não restaura conteúdo removido nem reativa conta; para isso existem as
      ações REMOVE_RECORDA e SUSPEND_USER/REACTIVATE_USER.

    Toda a operação (atualização de status + registro de auditoria) é atômica:
    se a auditoria falhar, o status não é alterado.
    """
    updated_count = admin_report_service.resolve_open_reports(
        db,
        target_type=target_type,
        target_id=target_id,
        new_status=body.status,
    )

    if updated_count == 0:
        raise HTTPException(status_code=409, detail=NO_REPORTS_TO_UPDATE_MESSAGE)

    target_recorda_id = target_id if target_type == TARGET_RECORDA else None
    target_user_id = target_id if target_type == TARGET_USER else None

    from_status = "OPEN" if body.status != "OPEN" else "RESOLVED/DISMISSED"

    moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_CHANGE_REPORT_STATUS,
        reason=body.reason,
        target_recorda_id=target_recorda_id,
        target_user_id=target_user_id,
        details={
            "target_type": target_type,
            "from": from_status,
            "to": body.status,
            "report_count": updated_count,
        },
    )

    db.commit()

    return ReportStatusChanged(updated_count=updated_count, status=body.status)


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


@router.post("/users/{user_id}/suspend", status_code=status.HTTP_200_OK)
def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> UserStatusResponse:
    user = admin_user_moderation_service.suspend_user(
        db,
        user_id,
        payload,
        current_admin,
        resolve_reports=report_repository.resolve_open_user_reports,
        record_action=moderation_service.record_action,
    )
    return UserStatusResponse(status_code=200, user_id=user_id, status=user.status)


@router.post("/users/{user_id}/reactivate", status_code=status.HTTP_200_OK)
def reactivate_user(
    user_id: UUID,
    payload: ReactivateUserRequest,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> UserStatusResponse:
    user = admin_user_moderation_service.reactivate_user(
        db,
        user_id,
        payload,
        current_admin,
        record_action=moderation_service.record_action,
    )
    return UserStatusResponse(status_code=200, user_id=user_id, status=user.status)


@router.post(
    "/recordas/{recorda_id}/removal",
    response_model=RemoveRecordaResponse,
    status_code=status.HTTP_200_OK,
)
def remove_recorda(
    recorda_id: UUID,
    payload: RemoveRecordaRequest,
    current_admin: Annotated[AppUser, Depends(get_current_admin_user)],
    db: Session = Depends(get_db),
) -> RemoveRecordaResponse:
    return admin_recorda_moderation_service.remove_recorda(
        db,
        recorda_id,
        payload,
        current_admin,
        resolve_reports=admin_report_service.resolve_open_reports,
        record_action=moderation_service.record_action,
    )
