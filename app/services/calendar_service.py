import uuid
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.time import get_month_utc_bounds, to_local
from app.models.recorda import Recorda
from app.schemas.calendar import CalendarDaySummary, MonthlyCalendarResponse


def get_monthly_calendar(
    db: Session,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> MonthlyCalendarResponse:
    start_utc, end_utc = get_month_utc_bounds(year, month)

    recordas = (
        db.query(Recorda)
        .filter(
            Recorda.user_id == user_id,
            Recorda.deleted_at.is_(None),
            Recorda.created_at >= start_utc,
            Recorda.created_at < end_utc,
        )
        .all()
    )

    grouped_by_day = defaultdict(list)
    for rec in recordas:
        local_date = to_local(rec.created_at).date()
        grouped_by_day[local_date].append(rec)

    days_summary: list[CalendarDaySummary] = []
    total_memories = 0

    for day_date in sorted(grouped_by_day.keys()):
        day_records = grouped_by_day[day_date]
        day_records.sort(key=lambda r: r.created_at)

        first_record = day_records[0]
        day_count = len(day_records)
        total_memories += day_count

        days_summary.append(
            CalendarDaySummary(
                date=day_date.isoformat(),
                day=day_date.day,
                count=day_count,
                thumbnail_url=first_record.media_url,
                media_type=first_record.media_type,
                first_recorda_id=first_record.recorda_id,
            )
        )

    return MonthlyCalendarResponse(
        year=year,
        month=month,
        total_memories=total_memories,
        active_days_count=len(days_summary),
        days=days_summary,
    )
