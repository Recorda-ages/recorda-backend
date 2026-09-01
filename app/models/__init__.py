"""ORM models. Import each module so its tables register on the Base metadata."""

from app.models.user import User
from app.models.recorda import Recorda

__all__ = ["User", "Recorda"]
