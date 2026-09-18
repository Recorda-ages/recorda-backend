from datetime import UTC, date, datetime

from app.core.time import SAO_PAULO, local_day_bounds, now_utc, to_local


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
