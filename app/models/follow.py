"""ORM model for the follow relationship between users."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

STATUS_PENDING = "PENDING"
STATUS_ACCEPTED = "ACCEPTED"


class Follow(Base):
    __tablename__ = "follow"
    __table_args__ = (
        UniqueConstraint(
            "follower_id", "following_id", name="uq_follow_follower_following"
        ),
        CheckConstraint("follower_id <> following_id", name="ck_follow_no_self_follow"),
        CheckConstraint("status IN ('PENDING', 'ACCEPTED')", name="ck_follow_status"),
    )

    follow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )