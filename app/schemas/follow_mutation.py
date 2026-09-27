from pydantic import BaseModel

from app.schemas.user import FollowStatus


class FollowMutationResult(BaseModel):
    follow_status: FollowStatus
