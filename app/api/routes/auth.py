from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserBasicResponse,
)
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return auth_service.login(db, payload)
    except auth_service.InvalidCredentialsError as exc:
        raise _invalid_credentials_error() from exc


@router.post(
    "/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return auth_service.register(db, payload)
    except user_service.UserAlreadyExistsError as exc:
        raise user_already_exists_error(exc) from exc


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> ResetPasswordResponse:
    try:
        return auth_service.reset_password(db, payload)
    except auth_service.ResetPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=auth_service.RESET_PASSWORD_ERROR_MESSAGE,
        ) from exc


@router.get("/me", response_model=UserBasicResponse)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserBasicResponse:
    return current_user


@router.get("/verify", response_model=UserBasicResponse)
def verify_token(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserBasicResponse:
    return current_user


def user_already_exists_error(
    exc: user_service.UserAlreadyExistsError,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"message": str(exc), "fields": exc.fields},
    )


def _invalid_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_service.INVALID_CREDENTIALS_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )
