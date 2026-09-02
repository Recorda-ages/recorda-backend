"""ORM models. Import each module so its tables register on the Base metadata."""

from app.models.recorda import Recorda
from app.models.user import User

__all__ = ["User", "Recorda"]
