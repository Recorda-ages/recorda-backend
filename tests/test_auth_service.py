import pytest

from app.core import security
from app.core.config import settings
from app.models import User
from app.schemas.auth import LoginRequest
from app.services import auth_service


def test_login_returns_access_token_and_basic_user_data(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", account_type="common")}

    response = auth_service.login(
        db, LoginRequest(username="alice", password="correct")
    )

    token_payload = security.decode_access_token(response.access_token)
    assert token_payload is not None
    assert token_payload["sub"] == "1"
    assert token_payload["username"] == "alice"
    assert token_payload["account_type"] == "common"
    assert response.token_type == "bearer"
    assert response.user.id == 1
    assert response.user.username == "alice"
    assert response.user.account_type == "common"


def test_login_raises_invalid_credentials_when_user_is_missing(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login(db, LoginRequest(username="missing", password="correct"))


def test_authenticate_user_returns_user_for_valid_credentials(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice")}

    user = auth_service.authenticate_user(db, "alice", "correct")

    assert user is db._users[1]


def test_authenticate_user_returns_none_for_wrong_password(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice")}

    assert auth_service.authenticate_user(db, "alice", "wrong") is None


def test_authenticate_user_returns_none_without_password_hash(db):
    db._users = {1: auth_user(id=1, username="alice", password_hash=None)}

    assert auth_service.authenticate_user(db, "alice", "correct") is None


def test_get_user_from_access_token_returns_user_when_token_matches(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", account_type="common")}
    token = security.create_access_token(
        subject="1",
        additional_claims={"username": "alice", "account_type": "common"},
    )

    user = auth_service.get_user_from_access_token(db, token)

    assert user is db._users[1]


def test_get_user_from_access_token_returns_none_when_username_changed(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    db._users = {1: auth_user(id=1, username="alice", account_type="common")}
    token = security.create_access_token(
        subject="1",
        additional_claims={"username": "old-alice", "account_type": "common"},
    )

    assert auth_service.get_user_from_access_token(db, token) is None


def auth_user(
    id: int,
    username: str,
    password: str = "correct",
    account_type: str = "common",
    password_hash: str | None = "",
) -> User:
    if password_hash == "":
        password_hash = security.hash_password(password)
    return User(
        id=id,
        name=username.title(),
        email=f"{username}@example.com",
        username=username,
        password_hash=password_hash,
        account_type=account_type,
    )
