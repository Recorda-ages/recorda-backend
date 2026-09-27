from typing import Literal

from pydantic import BaseModel


class FollowMutationResult(BaseModel):
    follow_status: Literal["nenhuma", "seguindo", "solicitado"]
