from uuid import UUID

from sqlalchemy import Row, Select, and_, delete, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.models.app_user import AppUser
from app.models.moderation_action import ModerationAction
from app.models.notification import (
    TYPE_COMMENT,
    TYPE_CONTENT_REMOVED,
    TYPE_FOLLOW_REQUEST,
    TYPE_LIKE,
    Notification,
)
from app.models.recorda import Recorda
from app.repositories._query import active_user_condition

Sender = aliased(AppUser)
RecordaAuthor = aliased(AppUser)


def _visible_for(recipient_id: UUID) -> Select:
    return (
        select(Notification)
        .outerjoin(Sender, Notification.sender_id == Sender.user_id)
        .outerjoin(Recorda, Notification.recorda_id == Recorda.recorda_id)
        .outerjoin(RecordaAuthor, Recorda.user_id == RecordaAuthor.user_id)
        .where(
            Notification.recipient_id == recipient_id,
            or_(Notification.sender_id.is_(None), active_user_condition(Sender)),
            or_(
                Notification.recorda_id.is_(None),
                and_(
                    active_user_condition(RecordaAuthor),
                    or_(
                        Recorda.deleted_at.is_(None),
                        Notification.type == TYPE_CONTENT_REMOVED,
                    ),
                ),
            ),
        )
    )


def list_for_recipient(
    db: Session, recipient_id: UUID, *, limit: int, offset: int
) -> list[Row]:
    query = (
        _visible_for(recipient_id)
        .add_columns(
            Sender.username,
            Sender.profile_picture_url,
            ModerationAction.reason.label("removal_reason"),
            ModerationAction.details.label("removal_details"),
            Recorda.song_title.label("recorda_song_title"),
            Recorda.media_url.label("recorda_media_url"),
            Recorda.media_type.label("recorda_media_type"),
            Recorda.song_cover_url.label("recorda_song_cover_url"),
        )
        .outerjoin(
            ModerationAction,
            Notification.moderation_action_id == ModerationAction.action_id,
        )
        .order_by(
            Notification.created_at.desc(),
            Notification.notification_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(db.execute(query).all())


def count_unread(db: Session, recipient_id: UUID) -> int:
    query = (
        _visible_for(recipient_id)
        .where(Notification.is_read.is_(False))
        .with_only_columns(func.count(Notification.notification_id))
        .order_by(None)
    )

    return db.execute(query).scalar_one()


def mark_all_as_read(db: Session, recipient_id: UUID) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == recipient_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    db.commit()

    return result.rowcount


def add(
    db: Session, notification: Notification, *, commit: bool = True
) -> Notification:
    db.add(notification)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(notification)

    return notification


def create_like(
    db: Session,
    *,
    recipient_id: UUID,
    sender_id: UUID,
    recorda_id: UUID,
) -> Notification:
    """Cria notificação de curtida sem commit (commit feito pelo service)."""
    notification = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        recorda_id=recorda_id,
        type=TYPE_LIKE,
    )
    db.add(notification)
    return notification


def create_comment(
    db: Session,
    *,
    recipient_id: UUID,
    sender_id: UUID,
    recorda_id: UUID,
    comment_id: UUID,
) -> Notification:
    notification = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        recorda_id=recorda_id,
        comment_id=comment_id,
        type=TYPE_COMMENT,
    )
    db.add(notification)
    return notification


def convert_follow_request(db: Session, follow_id: UUID, type_: str) -> None:
    """Troca o tipo do pedido de follow sem commit (commit feito pelo service)."""
    db.execute(
        update(Notification)
        .where(
            Notification.follow_id == follow_id,
            Notification.type == TYPE_FOLLOW_REQUEST,
        )
        .values(type=type_)
        .execution_options(synchronize_session=False)
    )


def delete_follow_request(db: Session, follow_id: UUID) -> None:
    """Apaga o pedido de follow sem commit (commit feito pelo service)."""
    db.execute(
        delete(Notification)
        .where(
            Notification.follow_id == follow_id,
            Notification.type == TYPE_FOLLOW_REQUEST,
        )
        .execution_options(synchronize_session=False)
    )
