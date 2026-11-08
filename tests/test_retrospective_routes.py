from datetime import UTC, datetime

import pytest

from tests.factories import add_recorda, add_user, auth_headers


def retrospective_url() -> str:
    return "/api/v1/users/me/retrospectives/available"


def test_get_available_periods(client, db):
    common_user = add_user(db, "Alice")
    common_headers = auth_headers(common_user)
    other_user = add_user(db, "Bob")
    add_recorda(db, common_user, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, common_user, created_at=datetime(2023, 2, 1, 3, 0, 0))
    add_recorda(db, common_user, created_at=datetime(2023, 2, 15, 3, 0, 0))
    add_recorda(
        db,
        common_user,
        created_at=datetime(2023, 3, 1, 3, 0, 0),
        deleted_at=datetime(2023, 4, 1, 3, 0, 0),
    )
    add_recorda(db, other_user, created_at=datetime(2023, 2, 1, 3, 0, 0))
    response = client.get(retrospective_url(), headers=common_headers)

    assert response.status_code == 200
    data = response.json()
    assert "periods" in data
    assert len(data["periods"]) == 3
    assert data["periods"][0]["period_type"] == "MONTHLY"
    assert data["periods"][0]["year"] == 2023
    assert data["periods"][0]["month"] == 2
    assert data["periods"][0]["label"] == "Fevereiro 2023"
    assert data["periods"][0]["total_memories"] == 2
    assert data["periods"][0]["is_preview"] is False
    assert data["periods"][2]["period_type"] == "YEARLY"
    assert data["periods"][2]["year"] == 2023
    assert data["periods"][2]["month"] is None
    assert data["periods"][2]["label"] == "Ano de 2023"
    assert data["periods"][2]["total_memories"] == 3
    assert data["periods"][2]["is_preview"] is False


def test_retrospective_require_authentication(client):
    assert client.get(retrospective_url()).status_code == 401


def test_retrospective_with_no_memories(client, db):
    user = add_user(db, "Alice")
    headers = auth_headers(user)
    response = client.get(retrospective_url(), headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "periods" in data
    assert len(data["periods"]) == 0


# --- Detalhes da retrospectiva (#149) ---

DETAILS_URL = "/api/v1/users/me/retrospectives"


def test_get_monthly_retrospective(client, db):
    owner = add_user(db, "owner")
    add_recorda(
        db,
        owner,
        created_at=datetime(2025, 10, 10, 15, tzinfo=UTC),
        song_preview_url="https://cdn.deezer.com/preview.mp3",
    )

    response = client.get(
        DETAILS_URL,
        params={"period_type": "MONTHLY", "year": 2025, "month": 10},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["label"] == "Outubro 2025"
    assert data["total_recordas"] == 1
    assert data["max_streak"] == 1
    assert data["engagement"] == {"likes_received": 0, "comments_received": 0}
    assert (
        data["featured_song"]["song_preview_url"]
        == "/api/v1/music/tracks/3135556/preview"
    )


def test_get_yearly_retrospective(client, db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=datetime(2025, 6, 10, 15, tzinfo=UTC))

    response = client.get(
        DETAILS_URL,
        params={"period_type": "YEARLY", "year": 2025},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["month"] is None


def test_period_without_recordas_returns_404(client, db):
    owner = add_user(db, "owner")

    response = client.get(
        DETAILS_URL,
        params={"period_type": "MONTHLY", "year": 2025, "month": 10},
        headers=auth_headers(owner),
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"] == "Nenhuma retrospectiva disponível para este período"


@pytest.mark.parametrize(
    "params",
    [
        {"period_type": "MONTHLY", "year": 2025},
        {"period_type": "YEARLY", "year": 2025, "month": 1},
        {"period_type": "MONTHLY", "year": 2025, "month": 13},
        {"period_type": "WEEKLY", "year": 2025},
        {"period_type": "MONTHLY", "month": 10},
    ],
)
def test_invalid_params_return_422(client, db, params):
    owner = add_user(db, "owner")

    response = client.get(DETAILS_URL, params=params, headers=auth_headers(owner))

    assert response.status_code == 422


def test_requires_authentication(client):
    response = client.get(
        DETAILS_URL, params={"period_type": "MONTHLY", "year": 2025, "month": 10}
    )

    assert response.status_code == 401
