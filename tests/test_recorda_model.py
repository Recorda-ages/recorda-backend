from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

from app.models import Recorda


def test_recorda_matches_database_contract():
    columns = Recorda.__table__.c

    assert set(columns.keys()) == {
        "recorda_id",
        "user_id",
        "media_url",
        "media_type",
        "description",
        "deezer_track_id",
        "song_title",
        "song_artist_name",
        "song_cover_url",
        "song_preview_url",
        "created_at",
        "deleted_at",
    }
    assert columns.recorda_id.primary_key
    assert isinstance(columns.recorda_id.type, PostgreSQLUUID)
    assert columns.recorda_id.type.as_uuid is True
    assert isinstance(columns.user_id.type, PostgreSQLUUID)
    assert columns.user_id.type.as_uuid is True
    assert str(columns.recorda_id.server_default.arg) == "gen_random_uuid()"
    assert isinstance(columns.media_url.type, String)
    assert isinstance(columns.media_type.type, String)
    assert isinstance(columns.description.type, Text)
    assert isinstance(columns.deezer_track_id.type, String)
    assert isinstance(columns.song_title.type, String)
    assert isinstance(columns.song_artist_name.type, String)
    assert isinstance(columns.song_cover_url.type, String)
    assert isinstance(columns.song_preview_url.type, String)
    assert isinstance(columns.created_at.type, DateTime)
    assert isinstance(columns.deleted_at.type, DateTime)
    assert columns.user_id.nullable is False
    assert columns.media_url.nullable is False
    assert columns.media_type.nullable is False
    assert columns.description.nullable is True
    assert columns.deezer_track_id.nullable is False
    assert columns.song_title.nullable is False
    assert columns.song_artist_name.nullable is False
    assert columns.song_cover_url.nullable is False
    assert columns.song_preview_url.nullable is True
    assert columns.created_at.nullable is False
    assert columns.deleted_at.nullable is True
    assert columns.created_at.type.timezone is True
    assert columns.deleted_at.type.timezone is True
    assert str(columns.created_at.server_default.arg) == "CURRENT_TIMESTAMP"


def test_recorda_fk_is_deferred_until_canonical_app_user_exists():
    assert not Recorda.__table__.c.user_id.foreign_keys


def test_recorda_has_media_type_constraint():
    constraints = [
        constraint
        for constraint in Recorda.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ]

    assert len(constraints) == 1
    assert "PHOTO" in str(constraints[0].sqltext)
    assert "VIDEO" in str(constraints[0].sqltext)


def test_recorda_allows_missing_preview_and_optional_description():
    recorda = Recorda(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        media_url="https://storage.example/photo.jpg",
        media_type="PHOTO",
        deezer_track_id="123",
        song_title="Song",
        song_artist_name="Artist",
        song_cover_url="https://example.com/cover.jpg",
        created_at=datetime.now(),
    )

    assert recorda.song_preview_url is None
    assert recorda.description is None


def test_recorda_does_not_include_out_of_scope_or_legacy_fields():
    columns = Recorda.__table__.c
    excluded_fields = {
        "album",
        "has_preview",
        "visibility",
        "memory_date",
        "location",
        "mentions",
        "updated_at",
        "id",
        "midia",
        "music",
        "data",
    }

    assert excluded_fields.isdisjoint(columns.keys())
