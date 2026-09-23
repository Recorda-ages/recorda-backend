import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

PHOTO = "PHOTO"
VIDEO = "VIDEO"


class Recorda(Base):
    __tablename__ = "recorda"
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('PHOTO', 'VIDEO')", name="ck_recorda_media_type"
        ),
        Index("ix_recorda_user_id_created_at", "user_id", desc("created_at")),
        Index("ix_recorda_deezer_track_id", "deezer_track_id"),
    )

    recorda_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=False
    )
    media_url: Mapped[str] = mapped_column(String, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deezer_track_id: Mapped[str] = mapped_column(String, nullable=False)
    song_title: Mapped[str] = mapped_column(String, nullable=False)
    song_artist_name: Mapped[str] = mapped_column(String, nullable=False)
    song_cover_url: Mapped[str] = mapped_column(String, nullable=False)
    song_preview_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
