"""Listas de Seguidores/Seguindo e remoção de um seguidor (T-E5.US22.BE.01)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.follow import FollowUser
from app.services import follow_service

router = APIRouter(prefix="/users", tags=["follows"])

USER_NOT_FOUND_MESSAGE = "Usuário não encontrado."
PRIVATE_ACCOUNT_MESSAGE = "Esta conta é privada."
FOLLOWER_NOT_FOUND_MESSAGE = "Este usuário não está entre os seus seguidores."


def _list_error(exc: Exception) -> HTTPException:
    if isinstance(exc, follow_service.PrivateAccountError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=PRIVATE_ACCOUNT_MESSAGE
        )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=USER_NOT_FOUND_MESSAGE
    )


@router.get("/{user_id}/followers", response_model=list[FollowUser])
def list_followers(
    user_id: UUID,
    q: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FollowUser]:
    """Quem segue o usuário informado."""
    try:
        return follow_service.list_followers(
            db, user_id, current_user, q=q, limit=limit, offset=offset
        )
    except (
        follow_service.UserNotFoundError,
        follow_service.PrivateAccountError,
    ) as exc:
        raise _list_error(exc) from exc


@router.get("/{user_id}/following", response_model=list[FollowUser])
def list_following(
    user_id: UUID,
    q: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FollowUser]:
    """Quem o usuário informado segue."""
    try:
        return follow_service.list_following(
            db, user_id, current_user, q=q, limit=limit, offset=offset
        )
    except (
        follow_service.UserNotFoundError,
        follow_service.PrivateAccountError,
    ) as exc:
        raise _list_error(exc) from exc


@router.delete("/me/followers/{follower_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_follower(
    follower_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove alguém dos próprios seguidores. O removido não é notificado."""
    if not follow_service.remove_follower(db, current_user, follower_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=FOLLOWER_NOT_FOUND_MESSAGE
        )
