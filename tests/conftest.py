import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.recorda import Recorda
from app.models.user import User


class FakeSession:
    """In-memory stand-in for a SQLAlchemy Session used by the repositories."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._recordas: dict[int, Recorda] = {}
        self._next_user_id = 1
        self._next_recorda_id = 1
        self._pending_add = None
        self._pending_delete = None

    def add(self, obj) -> None:
        self._pending_add = obj

    def commit(self) -> None:
        if self._pending_add is not None:
            obj = self._pending_add
            if isinstance(obj, Recorda):
                obj.id = self._next_recorda_id
                self._next_recorda_id += 1
                self._recordas[obj.id] = obj
            elif isinstance(obj, User):
                obj.id = self._next_user_id
                if getattr(obj, "account_type", None) is None:
                    obj.account_type = "common"
                self._next_user_id += 1
                self._users[obj.id] = obj
            self._pending_add = None
        if self._pending_delete is not None:
            obj = self._pending_delete
            if isinstance(obj, Recorda):
                self._recordas.pop(obj.id, None)
            elif isinstance(obj, User):
                self._users.pop(obj.id, None)
            self._pending_delete = None

    def refresh(self, obj) -> None:
        return None

    def get(self, model, obj_id: int):
        if model is User:
            return self._users.get(obj_id)
        if model is Recorda:
            return self._recordas.get(obj_id)
        return None

    def query(self, model):
        if model is User:
            return _Query(self._users)
        if model is Recorda:
            return _Query(self._recordas)
        raise AssertionError(f"FakeSession does not support {model}")

    def delete(self, obj) -> None:
        self._pending_delete = obj


class _Query:
    def __init__(self, store: dict) -> None:
        self._store = store
        self._filters: dict[str, object] = {}

    def all(self) -> list:
        return [obj for obj in self._store.values() if self._matches(obj)]

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self):
        return next(iter(self.all()), None)

    def _matches(self, obj) -> bool:
        return all(
            getattr(obj, key, None) == value for key, value in self._filters.items()
        )


@pytest.fixture
def db() -> FakeSession:
    return FakeSession()


@pytest.fixture
def user() -> User:
    return User(id=1, name="Alice", email="alice@example.com")


@pytest.fixture
def client(db: FakeSession):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sqlite_db():
    """Real SQLAlchemy session on in-memory SQLite.

    ``FakeSession`` above only knows how to store ``User``; suites that touch
    other tables (or rely on constraints and cascades) use this instead.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def sqlite_client(sqlite_db):
    def _override_get_db():
        yield sqlite_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
