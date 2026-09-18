"""Unit tests for the Recorda repository persistence layer."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.time import now_utc
from app.models import Recorda
from app.repositories import recorda_repository
from tests.factories import add_recorda, add_user


@pytest.fixture
def author(db):
    return add_user(db, "alice")


def test_get_all_returns_all(db, author):
    add_recorda(db, author)
    add_recorda(db, author, song_title="The Trooper")
    assert len(recorda_repository.get_all(db)) == 2


def test_get_all_empty(db):
    assert recorda_repository.get_all(db) == []


def test_get_all_skips_soft_deleted(db, author):
    live = add_recorda(db, author)
    add_recorda(db, author, deleted_at=now_utc())
    assert recorda_repository.get_all(db) == [live]


def test_get_by_id_returns_recorda(db, author):
    recorda = add_recorda(db, author)
    assert recorda_repository.get_by_id(db, recorda.recorda_id) is recorda


def test_get_by_id_missing_returns_none(db):
    assert recorda_repository.get_by_id(db, uuid.uuid4()) is None


def test_get_by_id_skips_soft_deleted(db, author):
    recorda = add_recorda(db, author, deleted_at=now_utc())
    assert recorda_repository.get_by_id(db, recorda.recorda_id) is None


def test_create_assigns_uuid_and_created_at(db, author):
    created = recorda_repository.create(
        db,
        Recorda(
            user_id=author.user_id,
            media_url="m",
            media_type="PHOTO",
            deezer_track_id="1",
            song_title="t",
            song_artist_name="a",
            song_cover_url="",
        ),
    )
    assert isinstance(created.recorda_id, uuid.UUID)
    assert created.created_at is not None


def test_create_rejects_unknown_author(db):
    orphan = Recorda(
        user_id=uuid.uuid4(),
        media_url="m",
        media_type="PHOTO",
        deezer_track_id="1",
        song_title="t",
        song_artist_name="a",
        song_cover_url="",
    )
    with pytest.raises(IntegrityError):
        recorda_repository.create(db, orphan)


def test_create_rejects_invalid_media_type(db, author):
    with pytest.raises(IntegrityError):
        add_recorda(db, author, media_type="GIF")


def test_save_commits_and_refreshes(db, author):
    recorda = add_recorda(db, author)
    recorda.description = "Outro"
    assert recorda_repository.save(db, recorda).description == "Outro"


def test_soft_delete_keeps_row(db, author):
    recorda = add_recorda(db, author)
    recorda_repository.soft_delete(db, recorda)
    assert recorda.deleted_at is not None
    assert db.get(Recorda, recorda.recorda_id) is recorda
