"""Endpoint tests for authentication/authorization enforcement on protected routes."""

from datetime import timedelta

from app.core import security
from app.core.config import settings
from app.models import AppUser
from app.models.app_user import ROLE_ADMIN
from tests.factories import add_user, auth_headers, token_for

AUTH_ME = "/api/v1/auth/me"
USERS = "/api/v1/users"

FORBIDDEN_BODY = {
    "error": {
        "code": "FORBIDDEN",
        "message": "Ação permitida apenas para administradores",
        "details": {},
    }
}


def test_protected_route_with_valid_token(client, db):
    alice = add_user(db, "alice")

    resp = client.get(AUTH_ME, headers=auth_headers(alice))

    assert resp.status_code == 200
    assert resp.json() == {
        "user_id": str(alice.user_id),
        "name": "Alice",
        "username": "alice",
        "role": "USER",
        "onboarding_completed": False,
    }


def test_protected_route_without_token_returns_401(client, db):
    resp = client.get(AUTH_ME)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_with_invalid_token_returns_401(client, db):
    resp = client.get(AUTH_ME, headers={"Authorization": "Bearer not-a-valid-token"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_with_expired_token_returns_401(client, db):
    alice = add_user(db, "alice")
    token = token_for(alice, expires_delta=timedelta(minutes=-1))

    resp = client.get(AUTH_ME, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_soft_deleted_user_token_returns_401(client, db):
    alice = add_user(db, "alice")
    headers = auth_headers(alice)
    alice.deleted_at = alice.created_at
    db.commit()

    assert client.get(AUTH_ME, headers=headers).status_code == 401


def test_common_user_cannot_access_admin_route(client, db):
    alice = add_user(db, "alice")

    resp = client.get(USERS, headers=auth_headers(alice))

    assert resp.status_code == 403
    assert resp.json() == FORBIDDEN_BODY


def test_admin_user_can_access_admin_route(client, db):
    admin = add_user(db, "admin", role=ROLE_ADMIN)

    resp = client.get(USERS, headers=auth_headers(admin))

    assert resp.status_code == 200


def test_anonymous_cannot_access_admin_route(client, db):
    resp = client.get(USERS)

    assert resp.status_code == 401


def test_public_signup_is_not_an_admin_route(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    resp = client.post(
        USERS,
        json={
            "name": "A",
            "email": "a@example.com",
            "username": "alice",
            "password": "secret",
        },
    )

    assert resp.status_code == 201
    stored = db.query(AppUser).filter_by(username="alice").one()
    assert stored.password_hash != "secret"
    assert security.verify_password("secret", stored.password_hash) is True
