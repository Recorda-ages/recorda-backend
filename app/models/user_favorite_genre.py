import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base


class UserFavoriteGenre(Base):
    __tablename__ = "user_favorite_genre"
    __table_args__ = (Index("ix_user_favorite_genre_genre_id", "genre_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), primary_key=True
    )
    genre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("genre.genre_id"), primary_key=True
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
