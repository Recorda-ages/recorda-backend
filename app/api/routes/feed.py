from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.app_user import AppUser
from app.schemas.feed import FeedPage
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/following", response_model=FeedPage)
def get_following_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedPage:
    """Feed com as Recordas dos usuários seguidos pelo usuário autenticado."""
    try:
        return feed_service.get_following_feed(
            db=db,
            current_user_id=current_user.user_id,
            cursor=cursor,
            limit=limit,
        )
    except feed_service.InvalidCursorError as exc:
        # Erro baseado ao cursor inválido, que pode ser um cursor mal formado ou um cursor que não existe mais (ex: a Recorda foi deletada).

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cursor inválido.",
        ) from exc
