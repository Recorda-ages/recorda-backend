"""Business rules for Recorda comments."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AppUser, RecordaComment
from app.repositories import (
    comment_repository,
    notification_repository,
    recorda_repository,
)
from app.schemas.comment import CommentRead
from app.services import recorda_service


class NotCommentOwnerError(Exception):
    """Raised when a user cannot delete a comment."""


def _read(comment: RecordaComment, author: AppUser) -> CommentRead:
    return CommentRead(
        comment_id=comment.comment_id,
        user_id=author.user_id,
        username=author.username,
        avatar_url=author.profile_picture_url,
        content=comment.content,
        created_at=comment.created_at,
    )


def list_for_recorda(
    db: Session, recorda_id: UUID, viewer: AppUser
) -> list[CommentRead] | None:
    if recorda_service.get_viewable_recorda(db, recorda_id, viewer) is None:
        return None
    return [
        CommentRead(
            comment_id=comment.comment_id,
            user_id=comment.user_id,
            username=username,
            avatar_url=avatar_url,
            content=comment.content,
            created_at=comment.created_at,
        )
        for comment, username, avatar_url in comment_repository.list_for_recorda(
            db, recorda_id
        )
    ]


def create(
    db: Session, recorda_id: UUID, author: AppUser, content: str
) -> CommentRead | None:
    recorda = recorda_service.get_viewable_recorda(db, recorda_id, author)
    if recorda is None:
        return None

    comment = RecordaComment(
        recorda_id=recorda_id, user_id=author.user_id, content=content
    )
    db.add(comment)
    db.flush()
    if recorda.user_id != author.user_id:
        notification_repository.create_comment(
            db,
            recipient_id=recorda.user_id,
            sender_id=author.user_id,
            recorda_id=recorda_id,
            comment_id=comment.comment_id,
        )
    db.commit()
    db.refresh(comment)
    return _read(comment, author)


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
