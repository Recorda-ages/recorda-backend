"""Shared authentication and authorization dependencies used by protected routes.

A single HTTPBearer scheme lives here so that every protected route reuses the
same token validation instead of duplicating it, and FastAPI registers the scheme
in the OpenAPI docs (enabling the Authorize button and lock icons).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User
from app.services import auth_service

ADMIN_ACCOUNT_TYPE = "admin"
FORBIDDEN_MESSAGE = "Ação permitida apenas para administradores"

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer token, or 401."""
    if credentials is None:
        raise _unauthorized()
    user = auth_service.get_user_from_access_token(db, credentials.credentials)
    if user is None:
        raise _unauthorized()
    return user


def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Resolve the authenticated user and require an administrative account."""
    if current_user.account_type != ADMIN_ACCOUNT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=FORBIDDEN_MESSAGE,
        )
    return current_user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_service.INVALID_CREDENTIALS_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )
