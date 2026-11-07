"""Testes HTTP do calendário mensal: GET /api/v1/users/me/calendar (US37)."""

from datetime import UTC, datetime

import pytest

from tests.factories import add_recorda, add_user, auth_headers

URL = "/api/v1/users/me/calendar"


def test_requires_authentication(client):
    response = client.get(URL, params={"year": 2026, "month": 11})

    assert response.status_code == 401


def test_returns_monthly_calendar_of_authenticated_user(client, db):
    owner = add_user(db, "owner")
    stranger = add_user(db, "stranger")
    recorda = add_recorda(
        db,
        owner,
        created_at=datetime(2026, 11, 16, 2, 59, tzinfo=UTC),  # 15/11 23:59 local
        media_url="/api/v1/recordas/media/thumb.jpg",
    )
    add_recorda(db, stranger, created_at=datetime(2026, 11, 20, 15, tzinfo=UTC))

    response = client.get(
        URL, params={"year": 2026, "month": 11}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json() == {
        "year": 2026,
        "month": 11,
        "total_memories": 1,
        "active_days_count": 1,
        "days": [
            {
                "date": "2026-11-15",
                "day": 15,
                "count": 1,
                "thumbnail_url": "/api/v1/recordas/media/thumb.jpg",
                "media_type": "PHOTO",
                "first_recorda_id": str(recorda.recorda_id),
            }
        ],
    }


def test_empty_month_returns_200(client, db):
    owner = add_user(db, "owner")

    response = client.get(
        URL, params={"year": 2026, "month": 2}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json()["days"] == []
    assert response.json()["total_memories"] == 0


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"year": 2026, "month": 0}, "month"),
        ({"year": 2026, "month": 13}, "month"),
        ({"year": 1969, "month": 5}, "year"),
        ({"year": 2101, "month": 5}, "year"),
        ({"year": "abc", "month": 5}, "year"),
        ({"month": 5}, "year"),
        ({"year": 2026}, "month"),
    ],
)
def test_invalid_period_returns_422(client, db, params, field):
    owner = add_user(db, "owner")

    response = client.get(URL, params=params, headers=auth_headers(owner))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [f["field"] for f in error["details"]["fields"]] == [field]


def test_calendar_is_documented_under_its_tag(client):
    operation = client.get("/openapi.json").json()["paths"][URL]["get"]

    assert operation["tags"] == ["calendar"]
    assert operation["security"] == [{"HTTPBearer": []}]
