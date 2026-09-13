"""Unit tests for the Recorda service orchestration layer."""

from app.models import Recorda, User
from app.schemas.recorda import RecordaCreate, RecordaUpdate
from app.services import recorda_service


def test_get_all_returns_all_recordas(db):
    db._recordas = {1: recorda(id=1, midia="Song", music="Song of Silence")}
    recordas = recorda_service.get_all(db)
    assert len(recordas) == 1


def test_get_by_id_returns_recorda_when_exists(db):
    db._recordas = {1: recorda(id=1, midia="Song", music="Song of Silence")}
    found = recorda_service.get_by_id(db, 1)
    assert found is not None
    assert found.id == 1
    assert found.midia == "Song"


def test_get_by_id_returns_none_when_missing(db):
    assert recorda_service.get_by_id(db, 999) is None


def test_create_persists_recorda_with_author_and_song(db):
    author = User(id=7, name="Alice", email="a@example.com", username="alice")
    created = recorda_service.create(
        db,
        RecordaCreate(
            midia="Hills",
            media_type="VIDEO",
            music="The Trooper",
            deezer_track_id="42",
            song_artist_name="Iron Maiden",
        ),
        author,
    )
    assert created.id == 1
    assert created.user_id == 7
    assert created.midia == "Hills"
    assert created.media_type == "VIDEO"
    assert created.music == "The Trooper"
    assert created.deezer_track_id == "42"
    assert created.song_artist_name == "Iron Maiden"
    assert created.song_cover_url is None
    assert created.data is not None
    assert 1 in db._recordas


def test_update_applies_fields_when_recorda_exists(db):
    db._recordas = {1: recorda(id=1, midia="Hills", music="The Tropper")}
    updated = recorda_service.update(db, 1, RecordaUpdate(midia="Song"))
    assert updated is not None
    assert updated.midia == "Song"
    assert updated.music == "The Tropper"


def test_update_partial_only_changes_given_fields(db):
    db._recordas = {1: recorda(id=1, midia="Hills", music="The Tropper")}
    updated = recorda_service.update(db, 1, RecordaUpdate(music="Song of Silence"))
    assert updated.music == "Song of Silence"
    assert updated.midia == "Hills"


def test_update_returns_none_when_recorda_missing(db):
    result = recorda_service.update(db, 999, RecordaUpdate(midia="Hills"))
    assert result is None


def test_delete_returns_true_when_recorda_exists(db):
    db._recordas = {1: recorda(id=1, midia="Hills")}
    assert recorda_service.delete(db, 1) is True
    assert 1 not in db._recordas


def test_delete_returns_false_when_recorda_missing(db):
    assert recorda_service.delete(db, 999) is False


def recorda(
    id: int,
    midia: str,
    music: str = "Song of Silence",
    description: str = "By Disturbed",
) -> Recorda:
    return Recorda(id=id, midia=midia, music=music, description=description)
