from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FollowUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    name: str
    profile_picture_url: str | None = None
