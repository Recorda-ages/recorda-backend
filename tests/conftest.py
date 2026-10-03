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


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

requires_postgres = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="requer PostgreSQL: defina TEST_DATABASE_URL (banco descartável)",
)


@pytest.fixture
def pg_db():
    """Sessão em PostgreSQL real, com o schema criado pelas migrations Alembic.

    Só roda quando `TEST_DATABASE_URL` está definida — o CI atual não tem
    PostgreSQL e os testes que dependem desta fixture são skipados.

    Serve para o que não existe no SQLite, como o trigger de imutabilidade de
    `moderation_action`. O schema `public` é recriado do zero, por isso o
    destino passa pela guarda de `tests.pg_guard` antes de qualquer DDL.
    """
    assert_disposable_database(
        TEST_DATABASE_URL,
        app_url=settings.database_url,
        allow_destructive=os.getenv(ALLOW_DESTRUCTIVE_ENV),
    )

    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")

    config = Config("alembic.ini")
    previous_url = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    try:
        command.upgrade(config, "head")
    finally:
        settings.database_url = previous_url

    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
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
