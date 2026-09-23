import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Genre(Base):
    __tablename__ = "genre"

    genre_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    deezer_genre_id: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True
    )
    picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
