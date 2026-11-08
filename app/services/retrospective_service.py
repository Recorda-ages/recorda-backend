from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import now_utc, to_local
from app.repositories import retrospective_repository
from app.schemas.retrospectives import AvailablePeriod, AvailablePeriodsResponse


def get_available_periods(db: Session, user_id: UUID) -> AvailablePeriodsResponse:

    recorda_dates = retrospective_repository.search_retrospectives(db, user_id)

    recorda_dates = [ensure_utc(date) for date in recorda_dates]

    recorda_dates_local = [to_local(date) for date in recorda_dates]

    if not recorda_dates_local:
        return AvailablePeriodsResponse(periods=[])

    current_utc = now_utc()

    current_sp = to_local(current_utc)

    current_year = current_sp.year
    current_month = current_sp.month

    monthly_counts: dict[tuple[int, int], int] = {}

    for recorda_date in recorda_dates_local:
        period_key = (recorda_date.year, recorda_date.month)
        monthly_counts[period_key] = monthly_counts.get(period_key, 0) + 1

    yearly_counts: dict[int, int] = {}

    for recorda_date in recorda_dates_local:
        period_key = recorda_date.year
        yearly_counts[period_key] = yearly_counts.get(period_key, 0) + 1

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

    for (year, month), count in monthly_counts.items():
        if (year, month) > (current_year, current_month):
            continue

        is_preview = (year, month) == (current_year, current_month)

        available_periods.append(
            AvailablePeriod(
                period_type="MONTHLY",
                year=year,
                month=month,
                label=f"{month_names[month - 1]} {year}",
                total_memories=count,
                is_preview=is_preview,
            )
        )

    for year, count in yearly_counts.items():
        if year >= current_year:
            continue

        available_periods.append(
            AvailablePeriod(
                period_type="YEARLY",
                year=year,
                month=None,
                label=f"Ano de {year}",
                total_memories=count,
                is_preview=False,
            )
        )

    available_periods.sort(key=lambda p: (p.year, p.month or 0), reverse=True)

    return AvailablePeriodsResponse(periods=available_periods)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value
