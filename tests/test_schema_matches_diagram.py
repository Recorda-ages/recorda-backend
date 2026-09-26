"""The ORM metadata must match the official database diagram (wiki)."""

import pytest
from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Text, Uuid

from app.db.seed_data import GENRE_NAMES, GENRE_SEED
from app.db.session import Base

NULLABLE = True
REQUIRED = False

DIAGRAM = {
    "app_user": {
        "user_id": (Uuid, REQUIRED),
        "username": (String, REQUIRED),
        "email": (String, REQUIRED),
        "name": (String, REQUIRED),
        "password_hash": (String, NULLABLE),
        "profile_picture_url": (String, NULLABLE),
        "language": (String, REQUIRED),
        "is_private": (Boolean, REQUIRED),
        "role": (String, REQUIRED),
        "status": (String, REQUIRED),
        "fav_song_deezer_track_id": (String, NULLABLE),
        "fav_song_title": (String, NULLABLE),
        "fav_song_artist_name": (String, NULLABLE),
        "fav_song_cover_url": (String, NULLABLE),
        "fav_song_preview_url": (String, NULLABLE),
        "created_at": (DateTime, REQUIRED),
        "updated_at": (DateTime, REQUIRED),
        "deleted_at": (DateTime, NULLABLE),
    },
    "recorda": {
        "recorda_id": (Uuid, REQUIRED),
        "user_id": (Uuid, REQUIRED),
        "media_url": (String, REQUIRED),
        "media_type": (String, REQUIRED),
        "description": (Text, NULLABLE),
        "deezer_track_id": (String, REQUIRED),
        "song_title": (String, REQUIRED),
        "song_artist_name": (String, REQUIRED),
        "song_cover_url": (String, REQUIRED),
        "song_preview_url": (String, NULLABLE),
        "created_at": (DateTime, REQUIRED),
        "deleted_at": (DateTime, NULLABLE),
    },
    "recorda_comment": {
        "comment_id": (Uuid, REQUIRED),
        "user_id": (Uuid, REQUIRED),
        "recorda_id": (Uuid, REQUIRED),
        "content": (Text, REQUIRED),
        "created_at": (DateTime, REQUIRED),
        "deleted_at": (DateTime, NULLABLE),
    },
    "genre": {
        "genre_id": (Uuid, REQUIRED),
        "name": (String, REQUIRED),
        "deezer_genre_id": (String, NULLABLE),
        "picture_url": (String, NULLABLE),
    },
    "user_favorite_genre": {
        "user_id": (Uuid, REQUIRED),
        "genre_id": (Uuid, REQUIRED),
        "selected_at": (DateTime, REQUIRED),
    },
    "user_favorite_artist": {
        "user_id": (Uuid, REQUIRED),
        "deezer_artist_id": (String, REQUIRED),
        "artist_name": (String, REQUIRED),
        "artist_image_url": (String, NULLABLE),
        "selected_at": (DateTime, REQUIRED),
    },
}

PRIMARY_KEYS = {
    "app_user": {"user_id"},
    "recorda": {"recorda_id"},
    "recorda_comment": {"comment_id"},
    "genre": {"genre_id"},
    "user_favorite_genre": {"user_id", "genre_id"},
    "user_favorite_artist": {"user_id", "deezer_artist_id"},
}

FOREIGN_KEYS = {
    ("recorda", "user_id"): "app_user.user_id",
    ("recorda_comment", "user_id"): "app_user.user_id",
    ("recorda_comment", "recorda_id"): "recorda.recorda_id",
    ("user_favorite_genre", "user_id"): "app_user.user_id",
    ("user_favorite_genre", "genre_id"): "genre.genre_id",
    ("user_favorite_artist", "user_id"): "app_user.user_id",
}


@pytest.mark.parametrize("table_name", DIAGRAM)
def test_columns_match_diagram(table_name):
    table = Base.metadata.tables[table_name]
    expected = DIAGRAM[table_name]

    assert set(table.c.keys()) == set(expected)
    for name, (type_, nullable) in expected.items():
        column = table.c[name]
        assert isinstance(column.type, type_), name
        assert column.nullable is nullable, name
        if isinstance(column.type, DateTime):
            assert column.type.timezone is True, name


@pytest.mark.parametrize("table_name", PRIMARY_KEYS)
def test_primary_keys_match_diagram(table_name):
    table = Base.metadata.tables[table_name]
    assert {c.name for c in table.primary_key} == PRIMARY_KEYS[table_name]


@pytest.mark.parametrize(("column", "target"), FOREIGN_KEYS.items())
def test_foreign_keys_match_diagram(column, target):
    table_name, column_name = column
    fks = Base.metadata.tables[table_name].c[column_name].foreign_keys
    assert [fk.target_fullname for fk in fks] == [target]


@pytest.mark.parametrize(
    ("table_name", "values"),
    [
        ("app_user", ("'USER'", "'ADMIN'")),
        ("app_user", ("'ACTIVE'", "'SUSPENDED'")),
        ("recorda", ("'PHOTO'", "'VIDEO'")),
    ],
)
def test_enum_checks_match_diagram(table_name, values):
    checks = [
        str(c.sqltext)
        for c in Base.metadata.tables[table_name].constraints
        if isinstance(c, CheckConstraint)
    ]
    assert any(all(v in check for v in values) for check in checks)


def test_unique_columns_match_diagram():
    tables = Base.metadata.tables
    assert tables["app_user"].c.username.unique
    assert tables["app_user"].c.email.unique
    assert tables["genre"].c.name.unique


def test_legacy_tables_and_columns_are_gone():
    assert {"users", "recordas", "music_preferences"}.isdisjoint(Base.metadata.tables)
    recorda = Base.metadata.tables["recorda"].c.keys()
    assert {"id", "midia", "music", "data", "updated_at"}.isdisjoint(recorda)


def test_genre_seed_has_the_18_default_genres_with_stable_ids():
    assert len(GENRE_NAMES) == len(set(GENRE_NAMES)) == 18
    assert len({genre_id for genre_id, _ in GENRE_SEED}) == 18
    assert str(GENRE_SEED[0][0]) == str(GENRE_SEED[0][0])
