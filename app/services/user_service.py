"""Business logic and orchestration for the User entity."""

from sqlalchemy.orm import Session

from app.core import security
from app.models import User
from app.repositories import user_repository
from app.schemas.user import UserChangeAccountType, UserCreate, UserUpdate

_COMMON_ACCOUNT_TYPE = "common"


def get_all(db: Session) -> list[User]:
    return user_repository.get_all(db)


def get_by_id(db: Session, user_id: int) -> User | None:
    return user_repository.get_by_id(db, user_id)


def create(db: Session, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        email=payload.email,
        username=payload.username,
        password_hash=security.hash_password(payload.password),
        account_type=_COMMON_ACCOUNT_TYPE,
    )
    return user_repository.create(db, user)


def update(db: Session, user_id: int, payload: UserUpdate) -> User | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    return user_repository.save(db, user)


def delete(db: Session, user_id: int) -> bool:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return False
    user_repository.delete(db, user)
    return True


def change_account_type(db: Session, user_id: int, payload: UserChangeAccountType) -> User | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    user.account_type = payload.account_type
    return user_repository.save(db, user)
