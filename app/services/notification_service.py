from uuid import UUID

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.models.follow import Follow
from app.models.notification import (
    TYPE_COMMENT,
    TYPE_FOLLOW_ACCEPTED,
    TYPE_FOLLOW_REQUEST,
    TYPE_LIKE,
    TYPE_MENTION,
    TYPE_NEW_FOLLOWER,
    Notification,
)
from app.models.recorda import Recorda
from app.repositories import notification_repository as repository
from app.schemas.notification import (
    NotificationItem,
    NotificationPage,
    NotificationSender,
)


def list_notifications(
    db: Session, recipient_id: UUID, *, limit: int, offset: int
) -> NotificationPage:
    rows = repository.list_for_recipient(db, recipient_id, limit=limit, offset=offset)

    return NotificationPage(
        items=[_to_item(row) for row in rows],
        unread_count=repository.count_unread(db, recipient_id),
    )


def mark_all_as_read(db: Session, recipient_id: UUID) -> int:
    return repository.mark_all_as_read(db, recipient_id)


def notify_follow_request(db: Session, follow: Follow) -> Notification | None:
    """Conta privada: avisa o dono do perfil que há um pedido aguardando."""
    return _create(
        db,
        recipient_id=follow.following_id,
        sender_id=follow.follower_id,
        type_=TYPE_FOLLOW_REQUEST,
        follow_id=follow.follow_id,
    )


def notify_follow_accepted(db: Session, follow: Follow) -> Notification | None:
    """Avisa quem pediu para seguir que o pedido foi aprovado."""
    return _create(
        db,
        recipient_id=follow.follower_id,
        sender_id=follow.following_id,
        type_=TYPE_FOLLOW_ACCEPTED,
        follow_id=follow.follow_id,
    )


def notify_new_follower(db: Session, follow: Follow) -> Notification | None:
    """Conta pública: avisa o dono do perfil que ganhou um seguidor."""
    return _create(
        db,
        recipient_id=follow.following_id,
        sender_id=follow.follower_id,
        type_=TYPE_NEW_FOLLOWER,
        follow_id=follow.follow_id,
    )


def notify_like(db: Session, recorda: Recorda, sender_id: UUID) -> Notification | None:
    """Avisa o autor da Recorda que ela foi curtida."""
    return _create(
        db,
        recipient_id=recorda.user_id,
        sender_id=sender_id,
        type_=TYPE_LIKE,
        recorda_id=recorda.recorda_id,
    )


def notify_comment(
    db: Session, recorda: Recorda, sender_id: UUID, comment_id: UUID
) -> Notification | None:
    """Avisa o autor da Recorda que ela recebeu um comentário."""
    return _create(
        db,
        recipient_id=recorda.user_id,
        sender_id=sender_id,
        type_=TYPE_COMMENT,
        recorda_id=recorda.recorda_id,
        comment_id=comment_id,
    )


def notify_mention(
    db: Session, recorda: Recorda, recipient_id: UUID
) -> Notification | None:
    """Avisa quem foi marcado em uma Recorda."""
    return _create(
        db,
        recipient_id=recipient_id,
        sender_id=recorda.user_id,
        type_=TYPE_MENTION,
        recorda_id=recorda.recorda_id,
    )


def _create(
    db: Session,
    *,
    recipient_id: UUID,
    sender_id: UUID | None,
    type_: str,
    recorda_id: UUID | None = None,
    comment_id: UUID | None = None,
    follow_id: UUID | None = None,
) -> Notification | None:
    if sender_id is not None and sender_id == recipient_id:
        return None

    return repository.add(
        db,
        Notification(
            recipient_id=recipient_id,
            sender_id=sender_id,
            type=type_,
            recorda_id=recorda_id,
            comment_id=comment_id,
            follow_id=follow_id,
        ),
    )


def _to_item(row: Row) -> NotificationItem:
    notification = row.Notification
    sender = None

    if notification.sender_id is not None:
        sender = NotificationSender(
            user_id=notification.sender_id,
            username=row.username,
            profile_picture_url=row.profile_picture_url,
        )

    return NotificationItem(
        notification_id=notification.notification_id,
        type=notification.type,
        is_read=notification.is_read,
        created_at=notification.created_at,
        sender=sender,
        recorda_id=notification.recorda_id,
        comment_id=notification.comment_id,
        follow_id=notification.follow_id,
    )
