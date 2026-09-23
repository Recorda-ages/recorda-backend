"""Unit tests for the AppUser repository persistence layer."""

import uuid

from app.core.time import now_utc
from app.models import AppUser
from app.repositories import user_repository
from tests.factories import add_user


def test_get_all_returns_all(db):
    add_user(db, "a")
    add_user(db, "b")
    assert len(user_repository.get_all(db)) == 2


def test_get_all_empty(db):
    assert user_repository.get_all(db) == []


def test_get_all_skips_soft_deleted(db):
    add_user(db, "a")
    deleted = add_user(db, "b", deleted_at=now_utc())
    assert deleted not in user_repository.get_all(db)


def test_get_by_id_returns_user(db):
    alice = add_user(db, "alice")
    assert user_repository.get_by_id(db, alice.user_id) is alice


def test_get_by_id_missing_returns_none(db):
    assert user_repository.get_by_id(db, uuid.uuid4()) is None


def test_get_by_id_skips_soft_deleted(db):
    alice = add_user(db, "alice", deleted_at=now_utc())
    assert user_repository.get_by_id(db, alice.user_id) is None


def test_get_by_email_returns_user_when_exists(db):
    add_user(db, "alice", email="a@e.com")
    result = user_repository.get_by_email(db, "a@e.com")
    assert result is not None
    assert result.email == "a@e.com"


def test_get_by_email_returns_none_when_missing(db):
    assert user_repository.get_by_email(db, "missing@e.com") is None


def test_credential_lookups_can_include_soft_deleted(db):
    add_user(db, "alice", deleted_at=now_utc())
    assert user_repository.get_by_username(db, "alice") is None
    assert user_repository.get_by_username(db, "alice", include_deleted=True)
    assert user_repository.get_by_email(db, "alice@example.com") is None
    assert user_repository.get_by_email(db, "alice@example.com", include_deleted=True)


def test_create_assigns_uuid_and_timestamps(db):
    created = user_repository.create(
        db, AppUser(name="A", email="a@e.com", username="a")
    )
    assert isinstance(created.user_id, uuid.UUID)
    assert created.created_at is not None
    assert created.updated_at is not None
    assert created.role == "USER"
    assert created.status == "ACTIVE"
    assert created.language == "pt-BR"
    assert created.is_private is False


def test_save_commits_and_refreshes(db):
    alice = add_user(db, "alice")
    alice.name = "Alicia"
    assert user_repository.save(db, alice).name == "Alicia"


def test_soft_delete_keeps_row(db):
    alice = add_user(db, "alice")
    user_repository.soft_delete(db, alice)
    assert alice.deleted_at is not None
    assert db.get(AppUser, alice.user_id) is alice
