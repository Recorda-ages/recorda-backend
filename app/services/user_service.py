"""Business logic and orchestration for the AppUser entity."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core import security
from app.models import AppUser
from app.models.app_user import ROLE_USER, ROLE_ADMIN
from app.repositories import user_repository
from app.schemas.user import UserChangeRole, UserCreate, UserUpdate

USERNAME_TAKEN_MESSAGE = "Este usuário já está cadastrado."
EMAIL_TAKEN_MESSAGE = "Este email já está cadastrado."
USER_ALREADY_EXISTS_MESSAGE = "Usuário ou email já cadastrado"


class UserAlreadyExistsError(Exception):
    def __init__(self, fields: list[dict[str, str]]) -> None:
        super().__init__(USER_ALREADY_EXISTS_MESSAGE)
        self.fields = fields


def get_all(db: Session) -> list[AppUser]:
    return user_repository.get_all(db)


def get_by_id(db: Session, user_id: UUID) -> AppUser | None:
    return user_repository.get_by_id(db, user_id)


def create(db: Session, payload: UserCreate) -> AppUser:
    ensure_unique_credentials(db, payload.username, payload.email)
    user = AppUser(
        name=payload.name,
        email=payload.email,
        username=payload.username,
        password_hash=security.hash_password(payload.password),
        role=ROLE_ADMIN,
    )
    return user_repository.create(db, user)


def ensure_unique_credentials(db: Session, username: str, email: str) -> None:
    fields = []
    if user_repository.get_by_username(db, username, include_deleted=True):
        fields.append({"field": "username", "message": USERNAME_TAKEN_MESSAGE})
    if user_repository.get_by_email(db, email, include_deleted=True):
        fields.append({"field": "email", "message": EMAIL_TAKEN_MESSAGE})
    if fields:
        raise UserAlreadyExistsError(fields)


def update(db: Session, user_id: UUID, payload: UserUpdate) -> AppUser | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    return user_repository.save(db, user)


def delete(db: Session, user_id: UUID) -> bool:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return False
    user_repository.soft_delete(db, user)
    return True


def change_role(db: Session, user_id: UUID, payload: UserChangeRole) -> AppUser | None:
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None
    user.role = payload.role
    return user_repository.save(db, user)
