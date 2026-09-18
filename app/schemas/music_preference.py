from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

MINIMUM_SELECTION = 3
MAXIMUM_SELECTION = 50

DeezerId = Annotated[int, Field(gt=0)]
Name = Annotated[str, Field(min_length=1, max_length=255)]


class MusicItem(BaseModel):
    """A genre or artist picked from Deezer, stored as sent by the client."""

    model_config = ConfigDict(from_attributes=True)

    deezer_id: DeezerId
    name: Name
    picture_url: str | None = None


class FavoriteTrack(BaseModel):
    deezer_id: DeezerId
    title: Name
    artist_name: Name
    cover_url: str = ""
    preview_url: str | None = None


MusicSelection = Annotated[
    list[MusicItem],
    Field(min_length=MINIMUM_SELECTION, max_length=MAXIMUM_SELECTION),
]


class MusicPreferencesCreate(BaseModel):
    genres: MusicSelection
    artists: MusicSelection
    favorite_track: FavoriteTrack

    @field_validator("genres", "artists")
    @classmethod
    def must_be_distinct(cls, items: list[MusicItem]) -> list[MusicItem]:
        """Repeats would only violate the table's primary key on insert."""
        if len({item.deezer_id for item in items}) != len(items):
            raise ValueError("não repita o mesmo item na seleção")
        return items


class MusicPreferencesRead(BaseModel):
    genres: list[MusicItem]
    artists: list[MusicItem]
    favorite_track: FavoriteTrack
    onboarding_completed: bool
