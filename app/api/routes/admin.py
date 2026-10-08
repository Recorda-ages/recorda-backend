"""Router administrativo /admin com a guarda de admin aplicada no router (T-E10.BE.01)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.repositories.report_repository import GroupOrder
from app.schemas.report import ReportGroupPage, ReportStatus, ReportTargetType
from app.services import admin_report_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)


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
