"""Upgrade e downgrade reais da 0010, em PostgreSQL descartável."""

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.core.config import settings
from tests.factories import add_recorda, add_user

pytestmark = pytest.mark.postgres

GENRE_OF = text("SELECT song_genre_name FROM recorda WHERE recorda_id = :id")
COUNT_OF = text("SELECT count(*) FROM recorda WHERE recorda_id = :id")


def _recorda_columns(pg_db) -> dict:
    return {c["name"]: c for c in inspect(pg_db.bind).get_columns("recorda")}


def test_downgrade_and_upgrade_keep_existing_recordas(pg_db, pg_database_url):
    author = add_user(pg_db, "author")
    with_genre = add_recorda(pg_db, author, song_genre_name="Pop").recorda_id
    without_genre = add_recorda(pg_db, author).recorda_id
    assert pg_db.scalar(GENRE_OF, {"id": with_genre}) == "Pop"
    assert pg_db.scalar(GENRE_OF, {"id": without_genre}) is None
    # Libera o lock da sessão em `recorda` para o DDL do Alembic não travar.
    pg_db.close()

    config = Config("alembic.ini")
    previous_url = settings.database_url
    settings.database_url = pg_database_url
    try:
        command.downgrade(config, "0009_content_removed")
        assert "song_genre_name" not in _recorda_columns(pg_db)
        assert pg_db.scalar(COUNT_OF, {"id": with_genre}) == 1
        assert pg_db.scalar(COUNT_OF, {"id": without_genre}) == 1
        pg_db.close()

        command.upgrade(config, "0010_recorda_song_genre_name")
        assert _recorda_columns(pg_db)["song_genre_name"]["nullable"] is True
        assert pg_db.scalar(GENRE_OF, {"id": with_genre}) is None
        assert pg_db.scalar(GENRE_OF, {"id": without_genre}) is None
    finally:
        settings.database_url = previous_url
