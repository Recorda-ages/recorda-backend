from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Recorda(Base):
    __tablename__ = "recordas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    midia: Mapped[str] = mapped_column(String, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
    music: Mapped[str] = mapped_column(String, nullable=True)
    deezer_track_id: Mapped[str | None] = mapped_column(String, nullable=True)
    song_artist_name: Mapped[str | None] = mapped_column(String, nullable=True)
    song_cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    data: Mapped[str] = mapped_column(String, nullable=True)
