from typing import Literal

from pydantic import BaseModel


class FollowRequestDecision(BaseModel):
    action: Literal["accept", "decline"]
