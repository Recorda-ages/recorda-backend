"""ORM models. Import each module so its tables register on the Base metadata."""

from app.models.music_preference import MusicPreference
from app.models.user import User

__all__ = ["MusicPreference", "User"]
