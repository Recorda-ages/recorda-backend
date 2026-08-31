"""Unit tests for the Recorda repository persistence layer."""

from app.models import Recorda
from app.repositories import recorda_repository


def test_get_all_returns_all(db):
    db._recordas = {
        1: Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        ),
        2: Recorda(
            id=2, midia="Hills", music="The Tropper", description="By Iron Maiden"
        ),
    }
    result = recorda_repository.get_all(db)
    assert len(result) == 2


def test_get_all_empty(db):
    assert recorda_repository.get_all(db) == []


def test_get_by_id_returns_(db):
    db._recordas = {
        5: Recorda(
            id=5, midia="Song", music="Song of Silence", description="By Disturbed"
        )
    }
    result = recorda_repository.get_by_id(db, 5)
    assert result is not None
    assert result.id == 5


def test_get_by_id_missing_returns_none(db):
    assert recorda_repository.get_by_id(db, 999) is None


def test_create_adds_commits_and_refreshes(db):
    incoming = Recorda(
        id=1, midia="Song", music="Song of Silence", description="By Disturbed"
    )
    created = recorda_repository.create(db, incoming)
    assert created.id == 1
    assert 1 in db._recordas
    assert db._recordas[1].midia == "Song"


def test_save_commits_and_refreshes(db):
    stashed = Recorda(id=1, midia="Song", music="Song of Silence")
    db._recordas = {1: stashed}
    db._next_id = 2
    saved = recorda_repository.save(db, stashed)
    assert saved is not None
    assert saved.midia == "Song"


def test_delete_removes_recorda_and_commits(db):
    db._recordas = {
        1: Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        )
    }
    recorda_repository.delete(
        db,
        Recorda(
            id=1, midia="Song", music="Song of Silence", description="By Disturbed"
        ),
    )
    assert 1 not in db._recordas
