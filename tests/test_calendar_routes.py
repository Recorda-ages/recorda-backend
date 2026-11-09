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
                "song_cover_url": "https://e.deezer.com/cover.jpg",
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


def test_daily_route_returns_authenticated_users_memories(client, db):
    owner = add_user(db, "owner")
    stranger = add_user(db, "stranger")
    recorda = add_recorda(
        db,
        owner,
        created_at=datetime(2026, 11, 8, 2, 59, tzinfo=UTC),
        song_preview_url="https://expired.deezer.test/preview.mp3",
    )
    add_recorda(db, stranger, created_at=datetime(2026, 11, 7, 15, tzinfo=UTC))
    add_recorda(db, owner, created_at=datetime(2026, 10, 1, 3, tzinfo=UTC))

    response = client.get(
        f"{URL}/day", params={"date": "2026-11-07"}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-11-07",
        "total_count": 1,
        "memories": [
            {
                "recorda_id": str(recorda.recorda_id),
                "author": {
                    "user_id": str(owner.user_id),
                    "username": "owner",
                    "avatar_url": None,
                },
                "media_url": recorda.media_url,
                "media_type": "PHOTO",
                "description": "By Disturbed",
                "deezer_track_id": "3135556",
                "song_title": "Song of Silence",
                "song_artist_name": "Disturbed",
                "song_cover_url": "https://e.deezer.com/cover.jpg",
                "song_preview_url": "/api/v1/music/tracks/3135556/preview",
                "song_genre_name": None,
                "created_at": "2026-11-08T02:59:00Z",
                "is_liked": False,
                "likes_count": 0,
                "comments_count": 0,
                "formatted_time": "23:59",
            }
        ],
        "previous_date_with_memories": "2026-10-01",
        "next_date_with_memories": None,
    }


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "invalid",
        "07/11/2026",
        "2026-11-7",
        "20261107",
        "2026-02-29",
        "2026-13-01",
        "2026-11-07T00:00:00",
        "1794009600",
        " 2026-11-07 ",
        "9999-12-31",
    ],
)
def test_daily_route_rejects_invalid_date(client, db, value):
    owner = add_user(db, "owner")

    response = client.get(
        f"{URL}/day",
        params={} if value is None else {"date": value},
        headers=auth_headers(owner),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [field["field"] for field in error["details"]["fields"]] == ["date"]


def test_daily_route_requires_authentication(client):
    response = client.get(f"{URL}/day", params={"date": "2026-11-07"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "target", ["2026-11-07", "2024-02-29", "0001-01-01", "9999-12-30"]
)
def test_daily_route_returns_empty_day(client, db, target):
    owner = add_user(db, "owner")

    response = client.get(
        f"{URL}/day", params={"date": target}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json() == {
        "date": target,
        "total_count": 0,
        "memories": [],
        "previous_date_with_memories": None,
        "next_date_with_memories": None,
    }


def test_daily_route_is_documented_in_openapi(client):
    operation = client.get("/openapi.json").json()["paths"][f"{URL}/day"]["get"]

    assert operation["tags"] == ["calendar"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert operation["parameters"][0]["name"] == "date"
    assert operation["parameters"][0]["required"] is True
    assert operation["parameters"][0]["schema"]["format"] == "date"
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DailyMemoriesResponse"
    }
