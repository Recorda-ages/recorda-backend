from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.calendar import (
    CalendarDate,
    DailyMemoriesResponse,
    MonthlyCalendarResponse,
)
from app.services import calendar_service, profile_service

router = APIRouter(prefix="/users/me/calendar", tags=["calendar"])


@router.get("", response_model=MonthlyCalendarResponse)
def get_monthly_calendar(
    year: int = Query(..., ge=1970, le=2100, description="Ano (YYYY)"),
    month: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyCalendarResponse:
    """Dias do mês com Recordas da conta autenticada, no fuso America/Sao_Paulo."""
    return calendar_service.get_monthly_calendar(db, current_user.user_id, year, month)


@router.get("/day", response_model=DailyMemoriesResponse)
def get_daily_memories(
    target_date: Annotated[
        CalendarDate,
        Query(alias="date", description="Dia local em America/Sao_Paulo (YYYY-MM-DD)"),
    ],
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyMemoriesResponse:
    """Memórias cronológicas do dia e datas vizinhas; dia vazio também retorna 200."""
    return calendar_service.get_daily_memories(db, current_user.user_id, target_date)


user_calendar_router = APIRouter(prefix="/users/{user_id}/calendar", tags=["calendar"])


def _viewable_owner(db: Session, user_id: UUID, viewer: AppUser) -> AppUser:
    try:
        return profile_service.get_viewable_owner(db, user_id, viewer)
    except profile_service.UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        ) from exc
    except profile_service.PrivateAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta é privada.",
        ) from exc


@user_calendar_router.get("", response_model=MonthlyCalendarResponse)
def get_user_monthly_calendar(
    user_id: UUID,
    year: int = Query(..., ge=1970, le=2100, description="Ano (YYYY)"),
    month: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyCalendarResponse:
    owner = _viewable_owner(db, user_id, current_user)
    return calendar_service.get_monthly_calendar(db, owner.user_id, year, month)


@user_calendar_router.get("/day", response_model=DailyMemoriesResponse)
def get_user_daily_memories(
    user_id: UUID,
    target_date: Annotated[
        CalendarDate,
        Query(alias="date", description="Dia local em America/Sao_Paulo (YYYY-MM-DD)"),
    ],
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyMemoriesResponse:
    owner = _viewable_owner(db, user_id, current_user)
    return calendar_service.get_daily_memories(
        db, owner.user_id, target_date, viewer_id=current_user.user_id
    )
