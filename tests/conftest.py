import os
from datetime import timedelta

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from alembic import command
from app.core.config import settings
from app.db.seed_data import GENRE_SEED
from app.db.session import Base, get_db
from app.main import app
from app.models import AppUser, Genre
from app.models.app_user import ROLE_ADMIN, ROLE_USER
from tests.factories import add_user, token_for
from tests.pg_guard import (
    ALLOW_DESTRUCTIVE_ENV,
    assert_disposable_database,
)


@pytest.fixture
def db():
    """Real SQLAlchemy session on in-memory SQLite, seeded like migration 0002."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    session.add_all(Genre(genre_id=gid, name=name) for gid, name in GENRE_SEED)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="session")
def pg_database_url():
    """Um container por execução; URLs externas continuam protegidas pela guarda."""
    external_url = os.getenv("TEST_DATABASE_URL")
    if external_url:
        assert_disposable_database(
            external_url,
            app_url=settings.database_url,
            allow_destructive=os.getenv(ALLOW_DESTRUCTIVE_ENV),
        )
        yield external_url
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(
        "postgres:16-alpine", dbname="test_recorda", driver="psycopg"
    ) as postgres:
        url = postgres.get_connection_url()
        assert_disposable_database(
            url, app_url=settings.database_url, allow_destructive="1"
        )
        yield url


@pytest.fixture
def pg_db(pg_database_url):
    """Schema migrado e recriado por teste, isolando commits e alterações de DDL."""
    engine = create_engine(pg_database_url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
            connection.exec_driver_sql("CREATE SCHEMA public")

        config = Config("alembic.ini")
        previous_url = settings.database_url
        settings.database_url = pg_database_url
        try:
            command.upgrade(config, "head")
        finally:
            settings.database_url = previous_url

        with Session(engine, autoflush=False) as session:
            yield session
    finally:
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
                connection.exec_driver_sql("CREATE SCHEMA public")
        finally:
            engine.dispose()


@pytest.fixture
def client(db: Session):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def common_user(db: Session) -> AppUser:
    return add_user(db, "usuario_comum", name="Usuário Comum", role=ROLE_USER)


@pytest.fixture
def admin_user(db: Session) -> AppUser:
    return add_user(db, "usuario_admin", name="Usuário Admin", role=ROLE_ADMIN)


@pytest.fixture
def common_user_token(common_user: AppUser) -> str:
    return token_for(common_user)


@pytest.fixture
def admin_user_token(admin_user: AppUser) -> str:
    return token_for(admin_user)


@pytest.fixture
def expired_token(common_user: AppUser) -> str:
    return token_for(common_user, expires_delta=timedelta(minutes=-5))
