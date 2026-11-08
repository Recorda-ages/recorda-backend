"""Calendário mensal de memórias do usuário autenticado (US37)."""

from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import local_month_bounds, to_local
from app.models import Recorda
from app.repositories import recorda_repository
from app.schemas.calendar import CalendarDaySummary, MonthlyCalendarResponse


def get_monthly_calendar(
    db: Session, user_id: UUID, year: int, month: int
) -> MonthlyCalendarResponse:
    """Agrupa as Recordas vivas do mês pelo dia local em America/Sao_Paulo.

    Exclusões pelo autor e pela moderação não aparecem.
    """
    start, end = local_month_bounds(year, month)
    recordas_by_day: dict[date, list[Recorda]] = defaultdict(list)
    for recorda in recorda_repository.list_by_user_between(db, user_id, start, end):
        recordas_by_day[_local_day(recorda.created_at)].append(recorda)

    days = [
        CalendarDaySummary(
            date=day,
            day=day.day,
            count=len(recordas),
            thumbnail_url=recordas[0].media_url,
            media_type=recordas[0].media_type,
            first_recorda_id=recordas[0].recorda_id,
        )
        for day, recordas in sorted(recordas_by_day.items())
    ]
    return MonthlyCalendarResponse(
        year=year,
        month=month,
        total_memories=sum(day.count for day in days),
        active_days_count=len(days),
        days=days,
    )


def _local_day(value: datetime) -> date:
    """O SQLite dos testes devolve datetime sem fuso; o valor gravado é UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return to_local(value).date()
