from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

MINIMUM_SELECTION = 3
MAXIMUM_SELECTION = 50


class MusicItem(BaseModel):
    """A single item picked from Deezer, stored as sent by the client."""

    model_config = ConfigDict(from_attributes=True)

    deezer_id: Annotated[int, Field(gt=0)]
    name: Annotated[str, Field(min_length=1, max_length=255)]


MusicSelection = Annotated[
    list[MusicItem],
    Field(min_length=MINIMUM_SELECTION, max_length=MAXIMUM_SELECTION),
]


class MusicPreferencesCreate(BaseModel):
    genres: MusicSelection
    artists: MusicSelection
    favorite_track: MusicItem

    @field_validator("genres", "artists")
    @classmethod
    def must_be_distinct(cls, items: list[MusicItem]) -> list[MusicItem]:
        """Repeats would only violate the table's unique constraint on insert."""
        if len({item.deezer_id for item in items}) != len(items):
            raise ValueError("não repita o mesmo item na seleção")
        return items


class MusicPreferencesRead(BaseModel):
    genres: list[MusicItem]
    artists: list[MusicItem]
    favorite_track: MusicItem
    onboarding_completed: bool
