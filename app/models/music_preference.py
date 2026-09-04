from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

GENRE = "genre"
ARTIST = "artist"
TRACK = "track"


class MusicPreference(Base):
    """One favourited Deezer item (genre, artist or track) of a user.

    Genres and artists make up the Perfil Musical (the only input to Afinidade
    Musical); the track is the standalone favourite song.
    """

    __tablename__ = "music_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "deezer_id", name="uq_music_preference"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    deezer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
