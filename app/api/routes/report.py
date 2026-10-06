"""Denúncias de conteúdo (T-E9.US40.BE.01)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.report import ReportCreate, ReportCreated
from app.services import report_service

# Sem prefixo: as denúncias ficam penduradas no recurso denunciado
# (/recordas/{id}/reports e, futuramente, /users/{id}/reports).
router = APIRouter(tags=["reports"])

_current_user = Depends(get_current_user)

RECORDA_NOT_FOUND_MESSAGE = "Recorda não encontrada."
ACCESS_DENIED_MESSAGE = "Você não tem permissão para ver esta Recorda."
SELF_REPORT_MESSAGE = "Você não pode denunciar sua própria Recorda."
DUPLICATE_REPORT_MESSAGE = "Você já denunciou esta Recorda."

_REPORT_ERRORS: dict[type[Exception], tuple[int, str]] = {
    report_service.ReportTargetNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        RECORDA_NOT_FOUND_MESSAGE,
    ),
    report_service.ReportAccessDeniedError: (
        status.HTTP_403_FORBIDDEN,
        ACCESS_DENIED_MESSAGE,
    ),
    report_service.SelfReportError: (
        status.HTTP_400_BAD_REQUEST,
        SELF_REPORT_MESSAGE,
    ),
    report_service.DuplicateReportError: (
        status.HTTP_409_CONFLICT,
        DUPLICATE_REPORT_MESSAGE,
    ),
}


@router.post(
    "/recordas/{recorda_id}/reports",
    response_model=ReportCreated,
    status_code=status.HTTP_201_CREATED,
)
def report_recorda(
    recorda_id: UUID,
    payload: ReportCreate,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> ReportCreated:
    try:
        return report_service.report_recorda(db, recorda_id, current_user, payload)
    except tuple(_REPORT_ERRORS) as exc:
        raise _report_http_error(exc) from exc


def _report_http_error(exc: Exception) -> HTTPException:
    status_code, message = _REPORT_ERRORS[type(exc)]
    return HTTPException(status_code=status_code, detail=message)
