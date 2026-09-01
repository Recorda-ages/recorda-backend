"""Endpoint tests for authentication/authorization enforcement on protected routes."""

from app.core import security
from app.core.config import settings
from app.models import User

AUTH_ME = "/api/v1/auth/me"
USERS = "/api/v1/users"

FORBIDDEN_BODY = {
    "error": {
        "code": "FORBIDDEN",
        "message": "Ação permitida apenas para administradores",
        "details": {},
    }
}


def test_protected_route_with_valid_token(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: user(1, username="alice", account_type="common")}
    token = token_for(db, 1, "alice", "common")

    resp = client.get(AUTH_ME, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json() == {"id": 1, "username": "alice", "account_type": "common"}


def test_protected_route_without_token_returns_401(client, db):
    resp = client.get(AUTH_ME)

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_with_invalid_token_returns_401(client, db):
    resp = client.get(AUTH_ME, headers={"Authorization": "Bearer not-a-valid-token"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_with_expired_token_returns_401(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    db._users = {1: user(1, username="alice", account_type="common")}
    token = token_for_generic(1, "alice", "common")

    resp = client.get(AUTH_ME, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_common_user_cannot_access_admin_route(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: user(1, username="alice", account_type="common")}
    token = token_for(db, 1, "alice", "common")

    resp = client.get(USERS, headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 403
    assert resp.json() == FORBIDDEN_BODY


def test_admin_user_can_access_admin_route(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: user(1, username="admin", account_type="admin")}
    token = token_for(db, 1, "admin", "admin")

    resp = client.get(USERS, headers={"Authorization": f"Bearer {token}"})

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
    stored = db._users[1]
    assert stored.password_hash != "secret"
    assert security.verify_password("secret", stored.password_hash) is True


def user(id: int, username: str, account_type: str) -> User:
    return User(
        id=id,
        name=username.title(),
        email=f"{username}@example.com",
        username=username,
        password_hash=security.hash_password("correct"),
        account_type=account_type,
    )


def token_for(db, user_id: int, username: str, account_type: str) -> str:
    assert user_id in db._users
    return security.create_access_token(
        subject=str(user_id),
        additional_claims={"username": username, "account_type": account_type},
    )


def token_for_generic(user_id: int, username: str, account_type: str) -> str:
    return security.create_access_token(
        subject=str(user_id),
        additional_claims={"username": username, "account_type": account_type},
    )
