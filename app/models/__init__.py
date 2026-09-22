"""ORM models. Import each module so its tables register on the Base metadata."""

from app.models.app_user import AppUser
from app.models.follow import Follow
from app.models.genre import Genre
from app.models.media import Media
from app.models.recorda import Recorda
from app.models.recorda_like import RecordaLike
from app.models.user_favorite_artist import UserFavoriteArtist
from app.models.user_favorite_genre import UserFavoriteGenre

__all__ = [
    "AppUser",
    "Follow",
    "Genre",
    "Media",
    "Recorda",
    "RecordaLike",
    "UserFavoriteArtist",
    "UserFavoriteGenre",
]