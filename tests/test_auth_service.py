import uuid

import pytest

from app.core import security
from app.core.config import settings
from app.models.app_user import ROLE_USER
from app.schemas.auth import LoginRequest
from app.services import auth_service
from tests.factories import add_user


def test_login_returns_access_token_and_basic_user_data(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    alice = add_user(db, "alice", password="correct")

    response = auth_service.login(
        db, LoginRequest(username="alice", password="correct")
    )

    token_payload = security.decode_access_token(response.access_token)
    assert token_payload is not None
    assert token_payload["sub"] == str(alice.user_id)
    assert token_payload["username"] == "alice"
    assert token_payload["role"] == ROLE_USER
    assert "account_type" not in token_payload
    assert response.token_type == "bearer"
    assert response.user.user_id == alice.user_id
    assert response.user.username == "alice"
    assert response.user.role == ROLE_USER


def test_login_raises_invalid_credentials_when_user_is_missing(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)

    with pytest.raises(auth_service.InvalidCredentialsError):
        auth_service.login(db, LoginRequest(username="missing", password="correct"))


def test_authenticate_user_returns_user_for_valid_credentials(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    alice = add_user(db, "alice", password="correct")

    assert auth_service.authenticate_user(db, "alice", "correct") is alice


def test_authenticate_user_returns_none_for_wrong_password(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    add_user(db, "alice", password="correct")

    assert auth_service.authenticate_user(db, "alice", "wrong") is None


def test_authenticate_user_returns_none_without_password_hash(db):
    add_user(db, "alice")

    assert auth_service.authenticate_user(db, "alice", "correct") is None


def test_authenticate_user_ignores_soft_deleted_user(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    alice = add_user(db, "alice", password="correct")
    alice.deleted_at = alice.created_at
    db.commit()

    assert auth_service.authenticate_user(db, "alice", "correct") is None


def test_reset_password_updates_user_password_and_returns_success(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    alice = add_user(db, "alice", password="old-password")

    result = auth_service.reset_password(
        db,
        auth_service.ResetPasswordRequest(
            email="alice@example.com", new_password="new-password-123"
        ),
    )

    assert result.message == "Senha redefinida com sucesso"
    assert security.verify_password("old-password", alice.password_hash) is False
    assert security.verify_password("new-password-123", alice.password_hash) is True


def test_reset_password_raises_for_unknown_user(db):
    with pytest.raises(auth_service.ResetPasswordError):
        auth_service.reset_password(
            db,
            auth_service.ResetPasswordRequest(
                email="missing@example.com",
                new_password="new-password-123",
            ),
        )


def test_get_user_from_access_token_returns_user_when_token_matches(db):
    alice = add_user(db, "alice")
    token = security.create_access_token(
        subject=str(alice.user_id),
        additional_claims={"username": "alice", "role": ROLE_USER},
    )

    assert auth_service.get_user_from_access_token(db, token) is alice


def test_get_user_from_access_token_returns_none_when_username_changed(db):
    alice = add_user(db, "alice")
    token = security.create_access_token(
        subject=str(alice.user_id),
        additional_claims={"username": "old-alice", "role": ROLE_USER},
    )

    assert auth_service.get_user_from_access_token(db, token) is None


@pytest.mark.parametrize("subject", ["1", "not-a-uuid", str(uuid.uuid4())])
def test_get_user_from_access_token_rejects_legacy_or_unknown_subject(db, subject):
    add_user(db, "alice")
    token = security.create_access_token(
        subject=subject, additional_claims={"username": "alice"}
    )

    assert auth_service.get_user_from_access_token(db, token) is None
