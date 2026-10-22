"""Validação do schema migrado e da API sobre PostgreSQL descartável."""

import uuid

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import CheckConstraint, inspect, select, text

from app.db.seed_data import GENRE_SEED
from app.db.session import Base, get_db
from app.main import app
from app.models import Genre, Recorda, RecordaComment, RecordaLike
from tests.factories import add_comment, add_user, auth_headers
from tests.test_recorda_routes import create_payload

pytestmark = pytest.mark.postgres


def test_migrated_schema_matches_models(pg_db):
    # UUID server defaults and GIN indexes live only in migrations (ADR 0001).
    def include_object(obj, name, type_, reflected, compare_to):
        return not (type_ == "index" and name and name.endswith("_trgm"))

    with pg_db.bind.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"include_object": include_object, "compare_server_default": False},
        )
        assert compare_metadata(context, Base.metadata) == []
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {
            "alembic_version"
        }
        for table in Base.metadata.sorted_tables:
            assert inspector.get_pk_constraint(table.name)["constrained_columns"] == [
                column.name for column in table.primary_key
            ]
            assert {
                check["name"] for check in inspector.get_check_constraints(table.name)
            } == {
                constraint.name
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            }


def test_postgres_specific_indexes_and_seed(pg_db):
    indexes = dict(
        pg_db.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'"
            )
        ).all()
    )
    for name, column in (
        ("ix_recorda_song_title_trgm", "song_title"),
        ("ix_recorda_song_artist_name_trgm", "song_artist_name"),
        ("ix_app_user_username_trgm", "username"),
    ):
        assert f"USING gin ({column} gin_trgm_ops)" in indexes[name]
    for name, target in (
        ("uq_report_reporter_recorda", "recorda_id"),
        ("uq_report_reporter_user", "reported_user_id"),
    ):
        assert "CREATE UNIQUE INDEX" in indexes[name]
        assert f"WHERE ({target} IS NOT NULL)" in indexes[name]
    assert set(pg_db.execute(select(Genre.genre_id, Genre.name)).all()) == set(
        GENRE_SEED
    )
    assert pg_db.scalar(text("SELECT version_num FROM alembic_version")) == (
        "0009_content_removed"
    )


def test_http_crud_and_authorization_on_postgres(pg_db):
    author = add_user(pg_db, "author")
    other = add_user(pg_db, "other")
    headers, other_headers = auth_headers(author), auth_headers(other)

    def override_db():
        yield pg_db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            prefix = "/api/v1/recordas"
            assert client.post(prefix, json=create_payload()).status_code == 401
            invalid = client.post(
                prefix, headers=headers, json=create_payload(media_type="INVALID")
            )
            assert invalid.status_code == 422
            response = client.post(prefix, headers=headers, json=create_payload())
            assert response.status_code == 201
            recorda_id = response.json()["recorda_id"]
            path = f"{prefix}/{recorda_id}"
            assert client.get(path, headers=headers).json()["recorda_id"] == recorda_id
            assert (
                client.put(
                    path, headers=other_headers, json={"description": "Intrusão"}
                ).status_code
                == 403
            )
            updated = client.put(
                path, headers=headers, json={"description": "Atualizada"}
            )
            assert updated.status_code == 200
            assert updated.json()["description"] == "Atualizada"
            stored = pg_db.get(Recorda, uuid.UUID(recorda_id))
            comment = add_comment(pg_db, other, stored)
            comment_id = comment.comment_id
            pg_db.add(RecordaLike(user_id=other.user_id, recorda_id=stored.recorda_id))
            pg_db.commit()
            assert client.delete(path, headers=other_headers).status_code == 403
            assert client.delete(path, headers=headers).status_code == 204
            assert client.get(path, headers=headers).status_code == 404
            assert client.delete(path, headers=headers).status_code == 404
            assert client.get(prefix, headers=headers).json() == []
            pg_db.expunge_all()
            assert pg_db.get(Recorda, uuid.UUID(recorda_id)).deleted_at is not None
            assert pg_db.get(RecordaComment, comment_id).deleted_at is not None
            assert list(pg_db.scalars(select(RecordaLike))) == []
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
