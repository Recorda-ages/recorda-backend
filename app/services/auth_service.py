"""Authentication orchestration for login and current-user flows."""

from sqlalchemy.orm import Session

from app.core import security
from app.models import User
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, LoginResponse, UserBasicResponse

INVALID_CREDENTIALS_MESSAGE = "Credenciais inválidas"

_DUMMY_PASSWORD_HASH: str | None = None


class InvalidCredentialsError(Exception):
    """Raised when login credentials cannot authenticate a user."""


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise InvalidCredentialsError

    token = security.create_access_token(
        subject=str(user.id),
        additional_claims={
            "username": user.username,
            "account_type": user.account_type,
        },
    )
    return LoginResponse(
        access_token=token,
        user=UserBasicResponse.model_validate(user),
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = user_repository.get_by_username(db, username)
    password_hash = user.password_hash if user and user.password_hash else None
    if password_hash is None:
        security.verify_password(password, _dummy_password_hash())
        return None
    if not security.verify_password(password, password_hash):
        return None
    return user


def get_user_from_access_token(db: Session, token: str) -> User | None:
    payload = security.decode_access_token(token)
    if payload is None:
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    user = user_repository.get_by_id(db, user_id)
    if user is None or user.username is None:
        return None

    token_username = payload.get("username")
    if isinstance(token_username, str) and token_username != user.username:
        return None
    return user


def _dummy_password_hash() -> str:
    global _DUMMY_PASSWORD_HASH
    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = security.hash_password("invalid-password")
    return _DUMMY_PASSWORD_HASH
