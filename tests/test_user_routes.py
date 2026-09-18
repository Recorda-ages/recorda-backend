"""Endpoint tests for the User API under /api/v1/users."""

import uuid

import pytest

from app.core import security
from app.core.config import settings
from app.models import AppUser
from app.models.app_user import ROLE_ADMIN, ROLE_USER
from tests.factories import add_user, auth_headers

PREFIX = "/api/v1/users"
MISSING_ID = uuid.uuid4()


@pytest.fixture
def admin_headers(db):
    return auth_headers(add_user(db, "admin", role=ROLE_ADMIN))


def test_list_users_requires_admin_and_returns_records(client, admin_headers):
    resp = client.get(PREFIX, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Admin"
    assert body[0]["email"] == "admin@example.com"
    assert body[0]["role"] == ROLE_ADMIN


def test_list_users_returns_all_records(client, db, admin_headers):
    add_user(db, "alice", name="A")
    resp = client.get(PREFIX, headers=admin_headers)
    assert resp.status_code == 200
    assert {u["name"] for u in resp.json()} == {"A", "Admin"}


def test_list_users_hides_soft_deleted(client, db, admin_headers):
    alice = add_user(db, "alice")
    alice.deleted_at = alice.created_at
    db.commit()
    resp = client.get(PREFIX, headers=admin_headers)
    assert [u["username"] for u in resp.json()] == ["admin"]


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
    assert body["name"] == "A"

    stored = db.get(AppUser, uuid.UUID(body["user_id"]))
    assert stored.username == "alice"
    assert stored.role == ROLE_USER
    assert stored.password_hash != "secret"
    assert security.verify_password("secret", stored.password_hash) is True
    assert security.verify_password("wrong", stored.password_hash) is False


def test_create_user_with_taken_username_returns_409(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    payload = {
        "name": "A",
        "email": "a@e.com",
        "username": "alice",
        "password": "secret",
    }
    assert client.post(PREFIX, json=payload).status_code == 201

    resp = client.post(PREFIX, json={**payload, "email": "other@e.com"})

    assert resp.status_code == 409
    fields = resp.json()["error"]["details"]["fields"]
    assert [f["field"] for f in fields] == ["username"]
    assert db.query(AppUser).count() == 1


def test_create_user_validates_missing_field(client):
    resp = client.post(PREFIX, json={"name": "A"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_user_does_not_expose_password(client, monkeypatch):
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


def test_get_user_returns_user(client, db, admin_headers):
    alice = add_user(db, "alice", name="A")
    resp = client.get(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "A"
    assert resp.json()["user_id"] == str(alice.user_id)


def test_get_user_returns_404_when_missing(client, admin_headers):
    resp = client.get(f"{PREFIX}/{MISSING_ID}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_get_user_rejects_non_uuid_id(client, admin_headers):
    resp = client.get(f"{PREFIX}/1", headers=admin_headers)
    assert resp.status_code == 422


def test_update_user_returns_200(client, db, admin_headers):
    alice = add_user(db, "alice", name="A", email="a@e.com")
    resp = client.put(
        f"{PREFIX}/{alice.user_id}", json={"name": "B"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"
    assert resp.json()["email"] == "a@e.com"


def test_update_user_returns_404_when_missing(client, admin_headers):
    resp = client.put(
        f"{PREFIX}/{MISSING_ID}", json={"name": "B"}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_delete_user_soft_deletes(client, db, admin_headers):
    alice = add_user(db, "alice")
    resp = client.delete(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert resp.status_code == 204
    db.refresh(alice)
    assert alice.deleted_at is not None
    again = client.get(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert again.status_code == 404


def test_delete_user_returns_404_when_missing(client, admin_headers):
    resp = client.delete(f"{PREFIX}/{MISSING_ID}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.parametrize("role", [ROLE_ADMIN, ROLE_USER])
def test_change_role(client, db, admin_headers, role):
    alice = add_user(db, "alice")
    resp = client.patch(
        f"{PREFIX}/{alice.user_id}/role", json={"role": role}, headers=admin_headers
    )
    assert resp.status_code == 200
    db.refresh(alice)
    assert alice.role == role


def test_change_role_returns_404_when_missing(client, admin_headers):
    resp = client.patch(
        f"{PREFIX}/{MISSING_ID}/role", json={"role": ROLE_ADMIN}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_change_role_rejects_invalid_value(client, db, admin_headers):
    alice = add_user(db, "alice")
    resp = client.patch(
        f"{PREFIX}/{alice.user_id}/role",
        json={"role": "superuser"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_change_role_requires_admin(client, db):
    alice = add_user(db, "alice")
    resp = client.patch(f"{PREFIX}/{alice.user_id}/role", json={"role": ROLE_ADMIN})
    assert resp.status_code == 401
