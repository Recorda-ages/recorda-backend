from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.app_user import AppUser
from app.schemas.feed import FeedPage
from app.services import general_feed_service

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/general", response_model=FeedPage)
def get_general_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedPage:
    """Feed da aba Geral: Recordas de autores visíveis ao usuário e com Afinidade Musical > 0."""
    try:
        return general_feed_service.get_general_feed(
            db=db,
            current_user_id=current_user.user_id,
            cursor=cursor,
            limit=limit,
        )
    except general_feed_service.InvalidCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cursor inválido.",
        ) from exc
