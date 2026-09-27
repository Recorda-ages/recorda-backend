from uuid import UUID

from sqlalchemy import Row, Select, func, or_, select, update
from sqlalchemy.orm import Session, aliased

from app.models.app_user import AppUser
from app.models.notification import TYPE_LIKE, Notification
from app.models.recorda import Recorda

Sender = aliased(AppUser)


def _visible_for(recipient_id: UUID) -> Select:
    return (
        select(Notification)
        .outerjoin(Sender, Notification.sender_id == Sender.user_id)
        .outerjoin(Recorda, Notification.recorda_id == Recorda.recorda_id)
        .where(
            Notification.recipient_id == recipient_id,
            or_(Notification.sender_id.is_(None), Sender.deleted_at.is_(None)),
            or_(Notification.recorda_id.is_(None), Recorda.deleted_at.is_(None)),
        )
    )


def list_for_recipient(
    db: Session, recipient_id: UUID, *, limit: int, offset: int
) -> list[Row]:
    query = (
        _visible_for(recipient_id)
        .add_columns(Sender.username, Sender.profile_picture_url)
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


def add(db: Session, notification: Notification) -> Notification:
    db.add(notification)
    db.commit()
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
