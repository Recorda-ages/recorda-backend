
from dataclasses import Field
from pickle import TRUE
from typing import Optional
from pydantic import BaseModel
from wsgiref.validate import validator


class SuspendUserRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    resolve_open_reports: bool = TRUE

    @validator("reason", pre=True)
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()

class ReactivateUserRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

    @validator("reason", pre=True)
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()