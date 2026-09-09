from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Recorda(Base):
    __tablename__ = "recorda"
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('PHOTO', 'VIDEO')",
            name="ck_recorda_media_type",
        ),
    )

    recorda_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
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
        server_default=text("CURRENT_TIMESTAMP"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
