"""Unit tests for the User service orchestration layer."""

import uuid

import pytest

from app.core import security
from app.core.config import settings
from app.schemas.user import UserChangeRole, UserCreate, UserUpdate
from app.services import user_service
from tests.factories import add_user


def test_get_all_returns_all_users(db):
    add_user(db, "alice")
    add_user(db, "bob")
    assert len(user_service.get_all(db)) == 2


def test_get_by_id_returns_user_when_exists(db):
    alice = add_user(db, "alice")
    found = user_service.get_by_id(db, alice.user_id)
    assert found is alice


def test_get_by_id_returns_none_when_missing(db):
    assert user_service.get_by_id(db, uuid.uuid4()) is None


def test_create_persists_user_and_hashes_password(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    created = user_service.create(
        db,
        UserCreate(
            name="Carol",
            email="c@example.com",
            username="carol",
            password="secret",
        ),
    )
    assert isinstance(created.user_id, uuid.UUID)
    assert created.name == "Carol"
    assert created.email == "c@example.com"
    assert created.username == "carol"
    assert created.role == "USER"
    assert created.onboarding_completed is False
    assert created.password_hash != "secret"
    assert security.verify_password("secret", created.password_hash) is True
    assert security.verify_password("wrong", created.password_hash) is False


def test_create_rejects_username_of_soft_deleted_user(db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    alice = add_user(db, "alice")
    user_service.delete(db, alice.user_id)

    with pytest.raises(user_service.UserAlreadyExistsError) as exc:
        user_service.create(
            db,
            UserCreate(
                name="A", email="alice@example.com", username="alice", password="x"
            ),
        )

    assert {f["field"] for f in exc.value.fields} == {"username", "email"}


def test_update_applies_fields_when_user_exists(db):
    alice = add_user(db, "alice", email="a@example.com")
    updated = user_service.update(db, alice.user_id, UserUpdate(name="Alicia"))
    assert updated.name == "Alicia"
    assert updated.email == "a@example.com"


def test_update_partial_only_changes_given_fields(db):
    alice = add_user(db, "alice")
    updated = user_service.update(
        db, alice.user_id, UserUpdate(email="new@example.com")
    )
    assert updated.email == "new@example.com"
    assert updated.name == "Alice"


def test_update_returns_none_when_user_missing(db):
    assert user_service.update(db, uuid.uuid4(), UserUpdate(name="X")) is None


def test_delete_soft_deletes_when_user_exists(db):
    alice = add_user(db, "alice")
    assert user_service.delete(db, alice.user_id) is True
    assert alice.deleted_at is not None
    assert user_service.get_by_id(db, alice.user_id) is None


def test_delete_returns_false_when_user_missing(db):
    assert user_service.delete(db, uuid.uuid4()) is False


def test_change_role_returns_none_when_user_missing(db):
    assert (
        user_service.change_role(db, uuid.uuid4(), UserChangeRole(role="ADMIN")) is None
    )
