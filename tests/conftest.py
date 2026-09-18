from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.seed_data import GENRE_SEED
from app.db.session import Base, get_db
from app.main import app
from app.models import AppUser, Genre
from app.models.app_user import ROLE_ADMIN, ROLE_USER
from tests.factories import add_user, token_for


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
