from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_DESCRIPTION_LENGTH = 500

ReportTargetType = Literal["RECORDA", "USER"]
ReportStatus = Literal["OPEN", "RESOLVED", "DISMISSED"]


class ReportCreate(BaseModel):
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("description", mode="before")
    @classmethod
    def blank_description_as_none(cls, value: Any) -> Any:
        # Descrição é opcional: vazio ou só espaços é o mesmo que não informar.
        if isinstance(value, str):
            return value.strip() or None
        return value


class ReportCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: UUID
    status: str
    created_at: datetime


class ReportTargetPreview(BaseModel):
    title: str
    subtitle: str | None = None
    image_url: str | None = None


class ReportGroup(BaseModel):
    target_type: ReportTargetType
    target_id: UUID
    status: ReportStatus
    report_count: int
    first_reported_at: datetime
    last_reported_at: datetime
    preview: ReportTargetPreview


class ReportGroupPage(BaseModel):
    items: list[ReportGroup]
    total: int
