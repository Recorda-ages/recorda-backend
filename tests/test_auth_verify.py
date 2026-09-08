import time

from fastapi.testclient import TestClient


def test_verify_returns_common_user(client: TestClient, common_user_token: str) -> None:
    response = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {common_user_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_type"] == "common"
    assert "password" not in body
    assert "password_hash" not in body


def test_verify_returns_admin_user(client: TestClient, admin_user_token: str) -> None:
    response = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {admin_user_token}"}
    )
    assert response.status_code == 200
    assert response.json()["account_type"] == "admin"


def test_verify_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/verify")
    assert response.status_code == 401


def test_verify_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/verify", headers={"Authorization": "Bearer token-invalido"}
    )
    assert response.status_code == 401


def test_verify_rejects_expired_token(client: TestClient, expired_token: str) -> None:
    response = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_verify_rejects_nonexistent_user(
    client: TestClient, db, common_user_token: str, common_user
) -> None:
    db.delete(common_user)
    db.commit()

    response = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {common_user_token}"}
    )
    assert response.status_code == 401


def test_verify_responds_within_timeout(
    client: TestClient, common_user_token: str
) -> None:
    start = time.monotonic()
    client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {common_user_token}"}
    )
    assert time.monotonic() - start < 3
