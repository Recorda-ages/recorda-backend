import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.user import User
from datetime import timedelta
from app.core import security


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
            if getattr(user, "account_type", None) is None:
                user.account_type = "common"
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
        self._filters: dict[str, object] = {}

    def all(self) -> list[User]:
        return [user for user in self._users.values() if self._matches(user)]

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def first(self) -> User | None:
        return next(iter(self.all()), None)

    def _matches(self, user: User) -> bool:
        return all(
            getattr(user, key, None) == value for key, value in self._filters.items()
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
def common_user(db: FakeSession) -> User:
    new_user = User(
        name="Usuário Comum",
        email="comum@example.com",
        username="usuario_comum",
        account_type="common",
    )
    db.add(new_user)
    db.commit()
    return new_user

@pytest.fixture
def admin_user(db: FakeSession) -> User:
    new_user = User(
        name="Usuário Admin",
        email="admin@example.com",
        username="usuario_admin",
        account_type="admin",
    )
    db.add(new_user)
    db.commit()
    return new_user

def _token_for(target_user: User, expires_delta: timedelta | None = None) -> str:
    return security.create_access_token(
        subject=str(target_user.id),
        additional_claims={
            "username": target_user.username,
            "account_type": target_user.account_type,
        },
        expires_delta=expires_delta,
    )

@pytest.fixture
def common_user_token(common_user: User) -> str:
    return _token_for(common_user)

@pytest.fixture
def admin_user_token(admin_user: User) -> str:
    return _token_for(admin_user)

@pytest.fixture
def expired_token(common_user: User) -> str:
    return _token_for(common_user, expires_delta=timedelta(minutes=-5))
