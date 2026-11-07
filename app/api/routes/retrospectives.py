from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.retrospectives import (
    AvailablePeriodsResponse,
    RetrospectiveDetailsResponse,
    RetrospectivePeriodQuery,
)
from app.services import retrospective_service

router = APIRouter(prefix="/users/me/retrospectives", tags=["retrospectives"])


@router.get("/available", response_model=AvailablePeriodsResponse)
def get_available_periods(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailablePeriodsResponse:
    return retrospective_service.get_available_periods(db, current_user.user_id)


RETROSPECTIVE_NOT_FOUND_MESSAGE = "Nenhuma retrospectiva disponível para este período"


@router.get("", response_model=RetrospectiveDetailsResponse)
def get_retrospective_details(
    period: Annotated[RetrospectivePeriodQuery, Query()],
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RetrospectiveDetailsResponse:
    """Métricas do mês ou ano da conta autenticada, no fuso America/Sao_Paulo."""
    try:
        return retrospective_service.get_retrospective_details(
            db, current_user.user_id, period
        )
    except retrospective_service.RetrospectiveNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=RETROSPECTIVE_NOT_FOUND_MESSAGE,
        ) from None
