"""Unit tests for the User service orchestration layer."""

from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service


def test_get_all_returns_all_users(db):
    db._users = {1: user(id=1, name="Alice"), 2: user(id=2, name="Bob")}
    users = user_service.get_all(db)
    assert len(users) == 2


def test_get_by_id_returns_user_when_exists(db):
    db._users = {1: user(id=1, name="Alice")}
    found = user_service.get_by_id(db, 1)
    assert found is not None
    assert found.id == 1
    assert found.name == "Alice"


def test_get_by_id_returns_none_when_missing(db):
    assert user_service.get_by_id(db, 999) is None


def test_create_persists_user(db):
    created = user_service.create(db, UserCreate(name="Carol", email="c@example.com"))
    assert created.id == 1
    assert created.name == "Carol"
    assert created.email == "c@example.com"
    assert 1 in db._users


def test_update_applies_fields_when_user_exists(db):
    db._users = {1: user(id=1, name="Alice", email="a@example.com")}
    updated = user_service.update(db, 1, UserUpdate(name="Alicia"))
    assert updated is not None
    assert updated.name == "Alicia"
    assert updated.email == "a@example.com"


def test_update_partial_only_changes_given_fields(db):
    db._users = {1: user(id=1, name="Alice", email="a@example.com")}
    updated = user_service.update(db, 1, UserUpdate(email="new@example.com"))
    assert updated.email == "new@example.com"
    assert updated.name == "Alice"


def test_update_returns_none_when_user_missing(db):
    result = user_service.update(db, 999, UserUpdate(name="X"))
    assert result is None


def test_delete_returns_true_when_user_exists(db):
    db._users = {1: user(id=1, name="Alice")}
    assert user_service.delete(db, 1) is True
    assert 1 not in db._users


def test_delete_returns_false_when_user_missing(db):
    assert user_service.delete(db, 999) is False


def user(id: int, name: str, email: str = "x@example.com") -> User:
    return User(id=id, name=name, email=email)
