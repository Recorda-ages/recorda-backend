from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.app_user import AppUser
from app.schemas.calendar import MonthlyCalendarResponse
from app.services import calendar_service

router = APIRouter(prefix="/users/me/calendar", tags=["calendar"])


@router.get("", response_model=MonthlyCalendarResponse)
def get_user_monthly_calendar(
    year: int = Query(..., ge=1970, le=2100, description="Ano da consulta"),
    month: int = Query(..., ge=1, le=12, description="Mês da consulta (1-12)"),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyCalendarResponse:
    return calendar_service.get_monthly_calendar(
        db=db,
        user_id=current_user.user_id,
        year=year,
        month=month,
    )
