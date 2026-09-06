"""Business logic for the onboarding music preferences."""

from sqlalchemy.orm import Session

from app.models import User
from app.models.music_preference import ARTIST, GENRE, TRACK, MusicPreference
from app.repositories import music_preference_repository
from app.schemas.music_preference import (
    MusicItem,
    MusicPreferencesCreate,
    MusicPreferencesRead,
)


def replace_for_user(
    db: Session, user: User, payload: MusicPreferencesCreate
) -> MusicPreferencesRead:
    """Persist the onboarding selection, replacing any previous one."""
    preferences = [
        MusicPreference(
            user_id=user.id, kind=kind, deezer_id=item.deezer_id, name=item.name
        )
        for kind, items in (
            (GENRE, payload.genres),
            (ARTIST, payload.artists),
            (TRACK, [payload.favorite_track]),
        )
        for item in items
    ]

    user.onboarding_completed = True
    music_preference_repository.replace_for_user(db, user.id, preferences)

    saved = {
        kind: [MusicItem.model_validate(p) for p in preferences if p.kind == kind]
        for kind in (GENRE, ARTIST, TRACK)
    }
    return MusicPreferencesRead(
        genres=saved[GENRE],
        artists=saved[ARTIST],
        favorite_track=saved[TRACK][0],
        onboarding_completed=user.onboarding_completed,
    )
