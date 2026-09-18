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
