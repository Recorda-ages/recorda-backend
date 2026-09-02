"""Unit tests for the User repository persistence layer."""

from app.models import User
from app.repositories import user_repository


def test_get_all_returns_all(db):
    db._users = {
        1: User(id=1, name="A", email="a@e.com"),
        2: User(id=2, name="B", email="b@e.com"),
    }
    result = user_repository.get_all(db)
    assert len(result) == 2


def test_get_all_empty(db):
    assert user_repository.get_all(db) == []


def test_get_by_id_returns_user(db):
    db._users = {5: User(id=5, name="A", email="a@e.com")}
    result = user_repository.get_by_id(db, 5)
    assert result is not None
    assert result.id == 5


def test_get_by_id_missing_returns_none(db):
    assert user_repository.get_by_id(db, 999) is None


def test_create_adds_commits_and_refreshes(db):
    incoming = User(name="A", email="a@e.com")
    created = user_repository.create(db, incoming)
    assert created.id == 1
    assert 1 in db._users
    assert db._users[1].name == "A"


def test_save_commits_and_refreshes(db):
    stashed = User(id=1, name="A", email="a@e.com")
    db._users = {1: stashed}
    db._next_id = 2
    saved = user_repository.save(db, stashed)
    assert saved is not None
    assert saved.name == "A"


def test_delete_removes_user_and_commits(db):
    db._users = {1: User(id=1, name="A", email="a@e.com")}
    user_repository.delete(db, User(id=1, name="A", email="a@e.com"))
    assert 1 not in db._users
