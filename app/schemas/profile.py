from typing import Literal
from uuid import UUID

from pydantic import BaseModel

FollowStatus = Literal["seguindo", "solicitado", "nenhuma"]


class ProfileFavoriteSong(BaseModel):
    deezer_track_id: str
    title: str
    artist_name: str
    cover_url: str
    preview_url: str | None


class ProfileCounts(BaseModel):
    recordas: int
    followers: int
    following: int


class ProfileStreak(BaseModel):
    current_days: int
    published_today: bool


class ProfileRelationship(BaseModel):
    is_self: bool
    follow_status: FollowStatus
    follow_id: UUID | None


class ProfileRead(BaseModel):
    user_id: UUID
    name: str
    username: str
    profile_picture_url: str | None
    is_private: bool
    counts: ProfileCounts | None  # None: perfil privado na #109
    favorite_song: ProfileFavoriteSong
    streak: ProfileStreak | None  # null até a #113
    relationship: ProfileRelationship
    can_view_content: bool
