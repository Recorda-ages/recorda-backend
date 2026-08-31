from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserBasicResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        return auth_service.login(db, payload)
    except auth_service.InvalidCredentialsError as exc:
        raise _invalid_credentials_error() from exc


@router.get("/me", response_model=UserBasicResponse)
def me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> UserBasicResponse:
    if credentials is None:
        raise _invalid_credentials_error()

    user = auth_service.get_user_from_access_token(db, credentials.credentials)
    if user is None:
        raise _invalid_credentials_error()
    return user


def _invalid_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_service.INVALID_CREDENTIALS_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )
