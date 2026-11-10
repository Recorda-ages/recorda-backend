"""Friends tagged in a Recorda; one occurrence per user and publication."""

from uuid import UUID

from sqlalchemy import ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RecordaMention(Base):
    __tablename__ = "recorda_mention"
    __table_args__ = (Index("ix_recorda_mention_user_id", "user_id"),)

    recorda_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), primary_key=True
    )
