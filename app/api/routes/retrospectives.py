from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.retrospectives import AvailablePeriodsResponse
from app.services import retrospectives_sevice

router = APIRouter(prefix="/users/me/retrospectives", tags=["retrospectives"])

@router.get("/available", response_model=AvailablePeriodsResponse)
def get_available_periods(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailablePeriodsResponse:
    return retrospectives_sevice.get_available_periods(db, current_user.user_id)