from datetime import UTC, date, datetime

from app.core.time import (
    SAO_PAULO,
    local_day_bounds,
    local_month_bounds,
    now_utc,
    to_local,
)


def test_now_utc_is_timezone_aware():
    assert now_utc().tzinfo is UTC


def test_to_local_converts_to_sao_paulo():
    local = to_local(datetime(2026, 9, 18, 2, 30, tzinfo=UTC))
    assert local.tzinfo == SAO_PAULO
    assert (local.day, local.hour) == (17, 23)


def test_local_day_bounds_are_sao_paulo_midnights_in_utc():
    start, end = local_day_bounds(date(2026, 9, 18))
    assert start == datetime(2026, 9, 18, 3, tzinfo=UTC)
    assert end == datetime(2026, 9, 19, 3, tzinfo=UTC)


def test_local_month_bounds_are_sao_paulo_midnights_in_utc():
    start, end = local_month_bounds(2026, 11)
    assert start == datetime(2026, 11, 1, 3, tzinfo=UTC)
    assert end == datetime(2026, 12, 1, 3, tzinfo=UTC)


def test_local_month_bounds_roll_over_december():
    start, end = local_month_bounds(2026, 12)
    assert start == datetime(2026, 12, 1, 3, tzinfo=UTC)
    assert end == datetime(2027, 1, 1, 3, tzinfo=UTC)


def test_local_month_bounds_follow_historical_daylight_saving():
    # O horário de verão de 2018/2019 terminou em 17/02/2019 (UTC-2 -> UTC-3).
    start, end = local_month_bounds(2019, 2)
    assert start == datetime(2019, 2, 1, 2, tzinfo=UTC)
    assert end == datetime(2019, 3, 1, 3, tzinfo=UTC)
