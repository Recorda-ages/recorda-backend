from datetime import datetime

from sqlalchemy.orm import Session

from app.core.time import now_utc, to_local, SAO_PAULO
from app.schemas.retrospectives import AvailablePeriod, AvailablePeriodsResponse
from app.models import AppUser

def get_available_periods(db: Session, user_id: int) -> AvailablePeriodsResponse:
    current_utc = now_utc()

    current_sp = to_local(current_utc, SAO_PAULO)

    current_year = current_sp.year
    current_month = current_sp.month

    total_memories = db.query(AppUser).filter(AppUser.user_id == user_id).count()

    is_preview = total_memories < 11

    available_periods = []

    available_periods.append(
        AvailablePeriod(
            period_type="MONTHLY",
            year=current_year,
            month=current_month,
            label=f"{current_month:02d}/{current_year}",
            total_memories=total_memories,
            is_preview=is_preview,
        )
    )

    available_periods.append(
        AvailablePeriod(
            period_type="YEARLY",
            year=current_year,
            month=None,
            label=f"{current_year}",
            total_memories=total_memories,
            is_preview=is_preview,
        )
    )

    return AvailablePeriodsResponse(periods=available_periods)

