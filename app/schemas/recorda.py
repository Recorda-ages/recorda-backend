from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MediaType = Literal["PHOTO", "VIDEO"]


class RecordaCreate(BaseModel):
    midia: str = Field(..., min_length=1)
    media_type: MediaType
    music: str = Field(..., min_length=1)
    deezer_track_id: str = Field(..., min_length=1)
    song_artist_name: str = Field(..., min_length=1)
    song_cover_url: str | None = None
    description: str | None = Field(None, max_length=2200)
    data: str | None = None


class RecordaUpdate(BaseModel):
    midia: str | None = None
    media_type: MediaType | None = None
    music: str | None = None
    deezer_track_id: str | None = None
    song_artist_name: str | None = None
    song_cover_url: str | None = None
    description: str | None = Field(None, max_length=2200)
    data: str | None = None


class RecordaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    midia: str | None
    media_type: str | None = None
    music: str | None
    deezer_track_id: str | None = None
    song_artist_name: str | None = None
    song_cover_url: str | None = None
    description: str | None
    data: str | None
