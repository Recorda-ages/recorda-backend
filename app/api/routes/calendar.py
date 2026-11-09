from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.calendar import (
    CalendarDate,
    DailyMemoriesResponse,
    MonthlyCalendarResponse,
)
from app.services import calendar_service

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
