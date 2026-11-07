from datetime import datetime

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
