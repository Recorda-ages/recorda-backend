"""Text comment posted by a user on a Recorda."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base


class RecordaComment(Base):
    __tablename__ = "recorda_comment"
    __table_args__ = (Index("ix_recorda_comment_recorda_id", "recorda_id"),)

    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=False
    )
    recorda_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
