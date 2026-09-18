"""Unit tests for the Recorda service orchestration layer."""

import uuid

import pytest

from app.schemas.recorda import RecordaCreate, RecordaUpdate
from app.services import recorda_service
from tests.factories import add_recorda, add_user


@pytest.fixture
def author(db):
    return add_user(db, "alice")


def test_get_all_returns_all_recordas(db, author):
    add_recorda(db, author)
    assert len(recorda_service.get_all(db)) == 1


def test_get_by_id_returns_recorda_when_exists(db, author):
    recorda = add_recorda(db, author)
    assert recorda_service.get_by_id(db, recorda.recorda_id) is recorda


def test_get_by_id_returns_none_when_missing(db):
    assert recorda_service.get_by_id(db, uuid.uuid4()) is None


def test_create_persists_recorda_with_author_and_song(db, author):
    created = recorda_service.create(
        db,
        RecordaCreate(
            media_url="Hills",
            media_type="VIDEO",
            song_title="The Trooper",
            deezer_track_id="42",
            song_artist_name="Iron Maiden",
        ),
        author,
    )
    assert isinstance(created.recorda_id, uuid.UUID)
    assert created.user_id == author.user_id
    assert created.media_url == "Hills"
    assert created.media_type == "VIDEO"
    assert created.song_title == "The Trooper"
    assert created.deezer_track_id == "42"
    assert created.song_artist_name == "Iron Maiden"
    assert created.song_cover_url == ""
    assert created.song_preview_url is None
    assert created.created_at is not None
    assert created.deleted_at is None


def test_update_changes_description(db, author):
    recorda = add_recorda(db, author)
    updated = recorda_service.update(
        db, recorda.recorda_id, RecordaUpdate(description="Outro"), author
    )
    assert updated.description == "Outro"
    assert updated.song_title == "Song of Silence"


def test_update_without_fields_keeps_recorda(db, author):
    recorda = add_recorda(db, author)
    updated = recorda_service.update(db, recorda.recorda_id, RecordaUpdate(), author)
    assert updated.description == "By Disturbed"


def test_update_returns_none_when_recorda_missing(db, author):
    assert (
        recorda_service.update(db, uuid.uuid4(), RecordaUpdate(description="x"), author)
        is None
    )


def test_update_rejects_other_user(db, author):
    recorda = add_recorda(db, author)
    other = add_user(db, "bob")
    with pytest.raises(recorda_service.NotRecordaOwnerError):
        recorda_service.update(
            db, recorda.recorda_id, RecordaUpdate(description="x"), other
        )


def test_delete_soft_deletes_when_recorda_exists(db, author):
    recorda = add_recorda(db, author)
    assert recorda_service.delete(db, recorda.recorda_id, author) is True
    assert recorda.deleted_at is not None
    assert recorda_service.get_by_id(db, recorda.recorda_id) is None


def test_delete_returns_false_when_recorda_missing(db, author):
    assert recorda_service.delete(db, uuid.uuid4(), author) is False
