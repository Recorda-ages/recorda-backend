from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

PeriodType = Literal["MONTHLY", "YEARLY"]

class AvailablePeriod(BaseModel):
    period_type: PeriodType
    year: int = Field(ge=1, le=9999)
    month: int | None = Field(ge=1, le=12)
    label: str
    total_memories : int = Field(ge=11)
    is_preview: bool

    @model_validator(mode="after")
    def validate_period(self) -> "AvailablePeriod":
        if self.period_type == "MONTHLY" and self.month is None:
            raise ValueError("Períodos mensais precisam informar o mês")
        if self.period_type == "YEARLY" and (
            self.month is not None or self.is_preview
        ):
            raise ValueError("Períodos anuais não têm mês nem prévia")
        return self

class AvailablePeriodsResponse(BaseModel):
    periods: list[AvailablePeriod]