from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import now_utc, to_local
from app.repositories import retrospectives_repository
from app.schemas.retrospectives import AvailablePeriod, AvailablePeriodsResponse


def get_available_periods(db: Session, user_id: UUID) -> AvailablePeriodsResponse:

    recorda_dates = retrospectives_repository.search_retrospectives(db, user_id)

    recorda_dates_local = [to_local(date) for date in recorda_dates]

    if not recorda_dates_local:
        return AvailablePeriodsResponse(periods=[])

    
    recorda_dates_local.sort(reverse=True)
    
    current_utc = now_utc()

    current_sp = to_local(current_utc)
    
    current_year = current_sp.year
    current_month = current_sp.month

    total_memories = len(recorda_dates_local)


    is_preview = total_memories < 11

    available_periods = []

    month_names = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    available_periods.append(
        AvailablePeriod(
            period_type="MONTHLY",
            year=current_year,
            month=current_month,
            label=f"{month_names[current_month - 1]} {current_year}",
            total_memories=total_memories,
            is_preview=is_preview,
        )
    )

    available_periods.append(
        AvailablePeriod(
            period_type="YEARLY",
            year=current_year,
            month=None,
            label=f"Ano de {current_year}",
            total_memories=total_memories,
            is_preview=is_preview,
        )
    )
    
    return AvailablePeriodsResponse(periods=available_periods)
