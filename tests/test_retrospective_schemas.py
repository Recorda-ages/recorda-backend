import pytest
from pydantic import ValidationError

from app.schemas.retrospectives import RetrospectivePeriodQuery


def test_monthly_query_requires_month():
    with pytest.raises(ValidationError):
        RetrospectivePeriodQuery(period_type="MONTHLY", year=2026)


def test_yearly_query_rejects_month():
    with pytest.raises(ValidationError):
        RetrospectivePeriodQuery(period_type="YEARLY", year=2025, month=1)


@pytest.mark.parametrize("month", [0, 13])
def test_query_rejects_month_out_of_range(month):
    with pytest.raises(ValidationError):
        RetrospectivePeriodQuery(period_type="MONTHLY", year=2026, month=month)


def test_query_accepts_valid_periods():
    monthly = RetrospectivePeriodQuery(period_type="MONTHLY", year=2026, month=10)
    yearly = RetrospectivePeriodQuery(period_type="YEARLY", year=2025)

    assert (monthly.year, monthly.month) == (2026, 10)
    assert (yearly.year, yearly.month) == (2025, None)
