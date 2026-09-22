import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base


class UserFavoriteArtist(Base):
    __tablename__ = "user_favorite_artist"
    __table_args__ = (
        Index("ix_user_favorite_artist_deezer_artist_id", "deezer_artist_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), primary_key=True
    )
    deezer_artist_id: Mapped[str] = mapped_column(String, primary_key=True)
    artist_name: Mapped[str] = mapped_column(String, nullable=False)
    artist_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
