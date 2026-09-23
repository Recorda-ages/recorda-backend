"""Authentication orchestration for login and current-user flows."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core import security
from app.models import AppUser
from app.repositories import user_repository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserBasicResponse,
)
from app.schemas.user import UserCreate
from app.services import user_service

INVALID_CREDENTIALS_MESSAGE = "Credenciais inválidas"
RESET_PASSWORD_ERROR_MESSAGE = "Não foi possível redefinir a senha"


class InvalidCredentialsError(Exception):
    """Raised when login credentials cannot authenticate a user."""


class ResetPasswordError(Exception):
    """Raised when the reset-password flow cannot complete."""


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise InvalidCredentialsError

    return _issue_login_response(user)


def register(db: Session, payload: RegisterRequest) -> LoginResponse:
    user = user_service.create(
        db,
        UserCreate(
            name=payload.name,
            email=payload.email,
            username=payload.username,
            password=payload.password,
        ),
    )
    return _issue_login_response(user)


def _issue_login_response(user: AppUser) -> LoginResponse:
    token = security.create_access_token(
        subject=str(user.user_id),
        additional_claims={"username": user.username, "role": user.role},
    )
    return LoginResponse(
        access_token=token,
        user=UserBasicResponse.model_validate(user),
    )


def reset_password(db: Session, payload: ResetPasswordRequest) -> ResetPasswordResponse:
    user = user_repository.get_by_email(db, payload.email)
    if user is None:
        raise ResetPasswordError(RESET_PASSWORD_ERROR_MESSAGE)

    user.password_hash = security.hash_password(payload.new_password)
    user_repository.save(db, user)
    return ResetPasswordResponse()


def authenticate_user(db: Session, username: str, password: str) -> AppUser | None:
    user = user_repository.get_by_username(db, username)
    if user is None or not user.password_hash:
        return None
    if not security.verify_password(password, user.password_hash):
        return None
    return user


def get_user_from_access_token(db: Session, token: str) -> AppUser | None:
    payload = security.decode_access_token(token)
    if payload is None:
        return None

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    user = user_repository.get_by_id(db, user_id)
    if user is None:
        return None

    token_username = payload.get("username")
    if isinstance(token_username, str) and token_username != user.username:
        return None
    return user
