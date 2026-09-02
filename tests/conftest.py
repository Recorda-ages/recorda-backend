import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.user import User


class FakeSession:
    """In-memory stand-in for a SQLAlchemy Session used by the repositories."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._next_id = 1
        self._pending_add: User | None = None
        self._pending_delete: User | None = None

    def add(self, user: User) -> None:
        self._pending_add = user

    def commit(self) -> None:
        if self._pending_add is not None:
            user = self._pending_add
            user.id = self._next_id
            self._next_id += 1
            self._users[user.id] = user
            self._pending_add = None
        if self._pending_delete is not None:
            self._users.pop(self._pending_delete.id, None)
            self._pending_delete = None

    def refresh(self, user: User) -> None:
        # Identity is shared with the store; nothing to copy back.
        return None

    def get(self, model, user_id: int) -> User | None:
        if model is not User:
            return None
        return self._users.get(user_id)

    def query(self, model):
        if model is not User:
            raise AssertionError("FakeSession only supports User")
        return _Query(self._users)

    def delete(self, user: User) -> None:
        self._pending_delete = user


class _Query:
    def __init__(self, users: dict[int, User]) -> None:
        self._users = users

    def all(self) -> list[User]:
        return list(self._users.values())


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
