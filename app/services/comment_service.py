"""Business rules for Recorda comments."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AppUser
from app.repositories import comment_repository, recorda_repository


class NotCommentOwnerError(Exception):
    """Raised when a user cannot delete a comment."""


def delete(db: Session, comment_id: UUID, current_user: AppUser) -> bool:
    comment = comment_repository.get_by_id(db, comment_id)
    if comment is None:
        return False

    if comment.user_id == current_user.user_id:
        comment_repository.soft_delete(db, comment)
        return True

    recorda = recorda_repository.get_by_id(db, comment.recorda_id)
    if recorda is None or recorda.user_id != current_user.user_id:
        raise NotCommentOwnerError

    comment_repository.soft_delete(db, comment)
    return True
