import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"
STATUS_ACTIVE = "ACTIVE"
STATUS_SUSPENDED = "SUSPENDED"
DEFAULT_LANGUAGE = "pt-BR"


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_app_user_role"),
        CheckConstraint("status IN ('ACTIVE', 'SUSPENDED')", name="ck_app_user_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=DEFAULT_LANGUAGE,
        server_default=DEFAULT_LANGUAGE,
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    role: Mapped[str] = mapped_column(
        String, nullable=False, default=ROLE_USER, server_default=ROLE_USER
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=STATUS_ACTIVE, server_default=STATUS_ACTIVE
    )
    fav_song_deezer_track_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fav_song_title: Mapped[str | None] = mapped_column(String, nullable=True)
    fav_song_artist_name: Mapped[str | None] = mapped_column(String, nullable=True)
    fav_song_cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    fav_song_preview_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        onupdate=now_utc,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def onboarding_completed(self) -> bool:
        return self.fav_song_deezer_track_id is not None
