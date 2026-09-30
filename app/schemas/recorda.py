from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.music_preview import public_preview_url

MediaType = Literal["PHOTO", "VIDEO"]


class RecordaCreate(BaseModel):
    media_url: str = Field(..., min_length=1)
    media_type: MediaType
    description: str | None = Field(None, max_length=2200)
    deezer_track_id: str = Field(..., min_length=1)
    song_title: str = Field(..., min_length=1)
    song_artist_name: str = Field(..., min_length=1)
    song_cover_url: str = ""
    song_preview_url: str | None = None


class RecordaUpdate(BaseModel):
    description: str | None = Field(None, max_length=2200)


class RecordaLikeState(BaseModel):
    likes_count: int
    is_liked: bool


class RecordaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recorda_id: UUID
    user_id: UUID
    media_url: str
    media_type: str
    description: str | None
    deezer_track_id: str
    song_title: str
    song_artist_name: str
    song_cover_url: str
    song_preview_url: str | None
    created_at: datetime

    @model_validator(mode="after")
    def _serve_preview_through_api(self) -> "RecordaRead":
        # The stored Deezer link expires; responses carry the API route that renews it.
        self.song_preview_url = public_preview_url(
            self.deezer_track_id, self.song_preview_url
        )
        return self


class RecordaAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    avatar_url: str | None


class RecordaDetail(BaseModel):
    recorda_id: UUID
    author: RecordaAuthor
    media_url: str
    media_type: str
    description: str | None
    deezer_track_id: str
    song_title: str
    song_artist_name: str
    song_cover_url: str
    song_preview_url: str | None
    created_at: datetime  # Data de Publicação
    is_liked: bool
    likes_count: int
