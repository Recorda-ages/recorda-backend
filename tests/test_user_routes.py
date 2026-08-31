"""Endpoint tests for the User API under /api/v1/users."""

from app.core import security
from app.core.config import settings
from app.models import User

PREFIX = "/api/v1/users"


def test_list_users_requires_admin_and_returns_records(client, db, monkeypatch):
    # admin_headers seeds the admin user into the store; since it is the only
    # record, the (admin-only) list endpoint returns just that admin.
    headers = admin_headers(db, monkeypatch, user_id=1)
    resp = client.get(PREFIX, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Admin"
    assert body[0]["email"] == "admin@example.com"


def test_list_users_returns_all_records(client, db, monkeypatch):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.get(PREFIX, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    names = {u["name"] for u in body}
    assert "A" in names
    assert "Admin" in names


def test_create_user_returns_201_and_hashes_password(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    resp = client.post(
        PREFIX,
        json={
            "name": "A",
            "email": "a@e.com",
            "username": "alice",
            "password": "secret",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["name"] == "A"

    stored = db._users[1]
    assert stored.username == "alice"
    assert stored.account_type == "common"
    assert stored.password_hash != "secret"
    assert security.verify_password("secret", stored.password_hash) is True
    assert security.verify_password("wrong", stored.password_hash) is False


def test_create_user_validates_missing_field(client):
    resp = client.post(PREFIX, json={"name": "A"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_user_does_not_expose_password(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    resp = client.post(
        PREFIX,
        json={
            "name": "A",
            "email": "a@e.com",
            "username": "alice",
            "password": "secret",
        },
    )
    body = resp.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert "hashed_password" not in body


def test_get_user_returns_user(client, db, monkeypatch):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.get(f"{PREFIX}/1", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "A"


def test_get_user_returns_404_when_missing(client, db, monkeypatch):
    headers = admin_headers(db, monkeypatch)
    resp = client.get(f"{PREFIX}/999", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_update_user_returns_200(client, db, monkeypatch):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.put(f"{PREFIX}/1", json={"name": "B"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"
    assert resp.json()["email"] == "a@e.com"


def test_update_user_returns_404_when_missing(client, db, monkeypatch):
    headers = admin_headers(db, monkeypatch)
    resp = client.put(f"{PREFIX}/999", json={"name": "B"}, headers=headers)
    assert resp.status_code == 404


def test_delete_user_returns_204(client, db, monkeypatch):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.delete(f"{PREFIX}/1", headers=headers)
    assert resp.status_code == 204
    assert 1 not in db._users


def test_delete_user_returns_404_when_missing(client, db, monkeypatch):
    headers = admin_headers(db, monkeypatch)
    resp = client.delete(f"{PREFIX}/999", headers=headers)
    assert resp.status_code == 404


def test_change_account_type_to_admin(client, db, monkeypatch):
    db._users = {
        1: User(id=1, name="Alice", email="alice@e.com", account_type="common")
    }
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.patch(
        f"{PREFIX}/1/account-type", json={"account_type": "admin"}, headers=headers
    )
    assert resp.status_code == 200
    assert db._users[1].account_type == "admin"


def test_change_account_type_to_common(client, db, monkeypatch):
    db._users = {1: User(id=1, name="Alice", email="alice@e.com", account_type="admin")}
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.patch(
        f"{PREFIX}/1/account-type", json={"account_type": "common"}, headers=headers
    )
    assert resp.status_code == 200
    assert db._users[1].account_type == "common"


def test_change_account_type_returns_404_when_missing(client, db, monkeypatch):
    headers = admin_headers(db, monkeypatch)
    resp = client.patch(
        f"{PREFIX}/999/account-type", json={"account_type": "admin"}, headers=headers
    )
    assert resp.status_code == 404


def test_change_account_type_rejects_invalid_value(client, db, monkeypatch):
    db._users = {
        1: User(id=1, name="Alice", email="alice@e.com", account_type="common")
    }
    headers = admin_headers(db, monkeypatch, user_id=2)
    resp = client.patch(
        f"{PREFIX}/1/account-type", json={"account_type": "superuser"}, headers=headers
    )
    assert resp.status_code == 422


def test_change_account_type_requires_admin(client, db):
    db._users = {
        1: User(id=1, name="Alice", email="alice@e.com", account_type="common")
    }
    resp = client.patch(f"{PREFIX}/1/account-type", json={"account_type": "admin"})
    assert resp.status_code == 401


def admin_headers(db, monkeypatch, *, user_id=1, username="admin") -> dict[str, str]:
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users[user_id] = User(
        id=user_id,
        name=username.title(),
        email=f"{username}@example.com",
        username=username,
        password_hash=security.hash_password("correct"),
        account_type="admin",
    )
    token = security.create_access_token(
        subject=str(user_id),
        additional_claims={"username": username, "account_type": "admin"},
    )
    return {"Authorization": f"Bearer {token}"}
