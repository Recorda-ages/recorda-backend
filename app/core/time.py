from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
CANONICAL_TIMEZONE = SAO_PAULO


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SAO_PAULO)


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=SAO_PAULO)
    return value.astimezone(UTC)


def local_day_bounds(local_day: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(local_day, time.min, tzinfo=SAO_PAULO)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def get_month_utc_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start_local = datetime(year, month, 1, 0, 0, 0, tzinfo=SAO_PAULO)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=SAO_PAULO)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=SAO_PAULO)

    return to_utc(start_local), to_utc(end_local)
