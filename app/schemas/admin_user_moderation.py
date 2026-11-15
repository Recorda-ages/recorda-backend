from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UserStatusResponse(BaseModel):
    status_code: Literal[200] = 200
    user_id: UUID
    status: str


class SuspendUserRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    resolve_open_reports: bool = True

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ReactivateUserRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value
