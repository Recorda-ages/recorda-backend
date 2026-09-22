from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
