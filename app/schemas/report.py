from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_DESCRIPTION_LENGTH = 500


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
