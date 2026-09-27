"""Notification entity for in-app social events."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

TYPE_FOLLOW_REQUEST = "FOLLOW_REQUEST"
TYPE_FOLLOW_ACCEPTED = "FOLLOW_ACCEPTED"
TYPE_NEW_FOLLOWER = "NEW_FOLLOWER"
TYPE_LIKE = "LIKE"
TYPE_COMMENT = "COMMENT"
TYPE_MENTION = "MENTION"

NOTIFICATION_TYPES = (
    TYPE_FOLLOW_REQUEST,
    TYPE_FOLLOW_ACCEPTED,
    TYPE_NEW_FOLLOWER,
    TYPE_LIKE,
    TYPE_COMMENT,
    TYPE_MENTION,
)

_TYPE_LIST = ", ".join(f"'{value}'" for value in NOTIFICATION_TYPES)


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint(f"type IN ({_TYPE_LIST})", name="ck_notification_type"),
        CheckConstraint(
            "recipient_id <> sender_id", name="ck_notification_no_self_notification"
        ),
        Index(
            "ix_notification_recipient_id_is_read_created_at",
            "recipient_id",
            "is_read",
            text("created_at DESC"),
        ),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="SET NULL"), nullable=True
    )
    recorda_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id", ondelete="SET NULL"), nullable=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    follow_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("follow.follow_id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
