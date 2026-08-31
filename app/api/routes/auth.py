from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserBasicResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return auth_service.login(db, payload)
    except auth_service.InvalidCredentialsError as exc:
        raise _invalid_credentials_error() from exc


@router.get("/me", response_model=UserBasicResponse)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserBasicResponse:
    return current_user


def _invalid_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_service.INVALID_CREDENTIALS_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )
