"""Calendário mensal de memórias: agrupamento por dia local em São Paulo (US37)."""

from datetime import UTC, date, datetime

from app.core.time import now_utc
from app.services.calendar_service import get_monthly_calendar
from tests.factories import add_recorda, add_user


def at(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_empty_month(db):
    owner = add_user(db, "owner")

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.model_dump() == {
        "year": 2026,
        "month": 11,
        "total_memories": 0,
        "active_days_count": 0,
        "days": [],
    }


def test_groups_same_day_and_uses_first_recorda_as_thumbnail(db):
    owner = add_user(db, "owner")
    # Inseridas fora de ordem: a primeira do dia vem do created_at, não da inserção.
    add_recorda(db, owner, created_at=at(2026, 11, 10, 20), media_url="/m/later.jpg")
    first = add_recorda(
        db,
        owner,
        created_at=at(2026, 11, 10, 13),
        media_url="/m/first.mp4",
        media_type="VIDEO",
    )

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.total_memories == 2
    assert result.active_days_count == 1
    [day] = result.days
    assert day.date == date(2026, 11, 10)
    assert day.day == 10
    assert day.count == 2
    assert day.first_recorda_id == first.recorda_id
    assert day.thumbnail_url == "/m/first.mp4"
    assert day.media_type == "VIDEO"


def test_late_night_publication_stays_on_local_day(db):
    owner = add_user(db, "owner")
    # 23:59 de 10/11 em São Paulo já é 11/11 em UTC.
    add_recorda(db, owner, created_at=at(2026, 11, 11, 2, 59))

    [day] = get_monthly_calendar(db, owner.user_id, 2026, 11).days

    assert day.date == date(2026, 11, 10)


def test_month_bounds_follow_sao_paulo_midnight(db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2026, 11, 1, 2, 59, 59))  # 31/10 23:59:59
    add_recorda(db, owner, created_at=at(2026, 11, 1, 3))  # 01/11 00:00
    add_recorda(db, owner, created_at=at(2026, 12, 1, 2, 59, 59))  # 30/11 23:59:59
    add_recorda(db, owner, created_at=at(2026, 12, 1, 3))  # 01/12 00:00

    november = get_monthly_calendar(db, owner.user_id, 2026, 11)
    october = get_monthly_calendar(db, owner.user_id, 2026, 10)
    december = get_monthly_calendar(db, owner.user_id, 2026, 12)

    assert [d.date for d in november.days] == [date(2026, 11, 1), date(2026, 11, 30)]
    assert november.total_memories == 2
    assert [d.date for d in october.days] == [date(2026, 10, 31)]
    assert [d.date for d in december.days] == [date(2026, 12, 1)]


def test_ignores_deleted_recordas_and_other_users(db):
    owner = add_user(db, "owner")
    other = add_user(db, "other")
    kept = add_recorda(db, owner, created_at=at(2026, 11, 5, 15))
    add_recorda(db, owner, created_at=at(2026, 11, 5, 12), deleted_at=now_utc())
    add_recorda(db, owner, created_at=at(2026, 11, 6, 12), deleted_at=now_utc())
    add_recorda(db, other, created_at=at(2026, 11, 5, 10))

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.total_memories == 1
    [day] = result.days
    assert (day.day, day.count, day.first_recorda_id) == (5, 1, kept.recorda_id)


def test_days_are_sorted_and_totals_add_up(db):
    owner = add_user(db, "owner")
    for created_at in [
        at(2026, 11, 20, 15),
        at(2026, 11, 3, 15),
        at(2026, 11, 20, 16),
        at(2026, 11, 12, 15),
        at(2026, 11, 3, 16),
    ]:
        add_recorda(db, owner, created_at=created_at)

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert [(d.day, d.count) for d in result.days] == [(3, 2), (12, 1), (20, 2)]
    assert result.total_memories == 5
    assert result.active_days_count == 3
