"""RecordaLike entity mapping user likes on Recordas."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base


class RecordaLike(Base):
    __tablename__ = "recorda_like"
    __table_args__ = (Index("ix_recorda_like_recorda_id", "recorda_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), primary_key=True
    )
    recorda_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
