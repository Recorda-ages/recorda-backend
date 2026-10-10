from pydantic import BaseModel, Field, field_validator


class SuspendUserRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    resolve_open_reports: bool = True

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class ReactivateUserRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()
