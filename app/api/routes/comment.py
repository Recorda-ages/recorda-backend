"""Comment deletion endpoints (T-E5.US25.BE.01)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.services import comment_service

router = APIRouter(prefix="/comments", tags=["comments"])

COMMENT_NOT_FOUND_MESSAGE = "Comentário não encontrado."
COMMENT_FORBIDDEN_MESSAGE = "Você não tem permissão para excluir este comentário."


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        was_deleted = comment_service.delete(db, comment_id, current_user)
    except comment_service.NotCommentOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=COMMENT_FORBIDDEN_MESSAGE,
        ) from exc
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=COMMENT_NOT_FOUND_MESSAGE,
        )
