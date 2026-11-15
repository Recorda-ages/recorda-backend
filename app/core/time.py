from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    return value.astimezone(SAO_PAULO)


def local_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=SAO_PAULO)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=SAO_PAULO)
    return start.astimezone(UTC), end.astimezone(UTC)


def local_month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Meia-noite do dia 1 do mês e do mês seguinte em São Paulo, em UTC."""
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    start = datetime.combine(date(year, month, 1), time.min, tzinfo=SAO_PAULO)
    end = datetime.combine(date(next_year, next_month, 1), time.min, tzinfo=SAO_PAULO)
    return start.astimezone(UTC), end.astimezone(UTC)


def local_year_bounds(year: int) -> tuple[datetime, datetime]:
    """Meia-noite de 1º de janeiro do ano e do ano seguinte em São Paulo, em UTC."""
    start = datetime.combine(date(year, 1, 1), time.min, tzinfo=SAO_PAULO)
    end = datetime.combine(date(year + 1, 1, 1), time.min, tzinfo=SAO_PAULO)
    return start.astimezone(UTC), end.astimezone(UTC)
