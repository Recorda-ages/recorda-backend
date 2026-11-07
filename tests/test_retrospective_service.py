from datetime import UTC, datetime

from app.services import retrospective_service
from tests.factories import add_recorda, add_user


def test_get_available_periods(db):
    user_id = add_user(db, "Alice")
    different_user_id = add_user(db, "Bob")

    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))

    blank_result = retrospective_service.get_available_periods(
        db, different_user_id.user_id
    )
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert blank_result.periods == []
    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[0].total_memories == 1

    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 1, 1, 30))
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[1].year == 2023
    assert result.periods[1].month == 1
    assert result.periods[1].total_memories == 2


def test_get_available_periods_excludes_deleted(db):
    user_id = add_user(db, "Alice")

    add_recorda(
        db,
        user_id,
        created_at=datetime(2023, 1, 1, 3, 0, 0),
        deleted_at=datetime(2023, 2, 1, 3, 0, 0),
    )
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert result.periods == []


def test_get_available_periods_ordering(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2022, 12, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))
    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2024, 3, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)

    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[1].year == 2023
    assert result.periods[1].month == 1
    assert result.periods[2].period_type == "YEARLY"
    assert result.periods[2].year == 2023
    assert result.periods[2].month is None
    assert result.periods[3].year == 2022
    assert result.periods[3].month == 12
    assert result.periods[4].period_type == "YEARLY"
    assert result.periods[4].year == 2022
    assert result.periods[4].month is None

    monthly_indexes_2023 = [
        i
        for i, period in enumerate(result.periods)
        if period.period_type == "MONTHLY" and period.year == 2023
    ]
    yearly_index_2023 = next(
        i
        for i, period in enumerate(result.periods)
        if period.period_type == "YEARLY" and period.year == 2023
    )

    assert monthly_indexes_2023
    assert max(monthly_indexes_2023) < yearly_index_2023


def test_get_available_test_is_preview(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))

    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2023, 2, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)
    february = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 2
    )
    january = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 1
    )

    assert february.is_preview is True
    assert january.is_preview is False


def test_get_available_periods_includes_completed_year_only(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2022, 1, 15, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2022, 12, 15, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 10, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 3, 10, 3, 0, 0))

    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2023, 2, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)

    annual_2022 = next(
        p for p in result.periods if p.period_type == "YEARLY" and p.year == 2022
    )
    february_2023 = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 2
    )

    assert annual_2022.label == "Ano de 2022"
    assert annual_2022.total_memories == 2
    assert annual_2022.is_preview is False
    assert february_2023.label == "Fevereiro 2023"
    assert february_2023.is_preview is True
    assert not any(p.period_type == "YEARLY" and p.year == 2023 for p in result.periods)
    assert not any(
        p.period_type == "MONTHLY" and p.year == 2023 and p.month == 3
        for p in result.periods
    )


def test_ensure_utc_returns_utc_datetime():
    dt_naive = datetime(2023, 1, 1, 12, 0, 0)
    dt_utc = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

    assert retrospective_service.ensure_utc(dt_naive) == dt_utc
    assert retrospective_service.ensure_utc(dt_utc) == dt_utc


def test_ensure_utc_preserves_timezone():
    dt_with_tz = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert retrospective_service.ensure_utc(dt_with_tz) == dt_with_tz
