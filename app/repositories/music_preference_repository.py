"""Persistence and query access for the MusicPreference entity."""

from sqlalchemy.orm import Session

from app.models import MusicPreference


def replace_for_user(
    db: Session, user_id: int, preferences: list[MusicPreference]
) -> list[MusicPreference]:
    """Swap every preference of the user for the given ones, atomically."""
    db.query(MusicPreference).filter_by(user_id=user_id).delete()
    db.add_all(preferences)
    db.commit()
    return preferences
