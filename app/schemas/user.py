from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.recorda import RecordaRead

FollowStatus = Literal["seguindo", "solicitado", "nenhuma"]


class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    username: str
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserChangeRole(BaseModel):
    role: Literal["USER", "ADMIN"]


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    role: str


class UserSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    avatar_url: str | None
    follow_status: FollowStatus


class ProfileFavoriteSong(BaseModel):
    deezer_track_id: str
    title: str
    artist_name: str
    cover_url: str
    preview_url: str | None


class ProfileGenre(BaseModel):
    genre_id: UUID
    name: str


class ProfileArtist(BaseModel):
    deezer_artist_id: str
    name: str
    image_url: str | None


class UserProfileRead(BaseModel):
    user_id: UUID
    username: str
    name: str
    profile_picture_url: str | None
    favorite_song: ProfileFavoriteSong
    favorite_genres: list[ProfileGenre]
    favorite_artists: list[ProfileArtist]
    recordas: list[RecordaRead]
