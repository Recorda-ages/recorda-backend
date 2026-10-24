"""Schemas for the administrative removal of Recordas."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

Reason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class RemoveRecordaRequest(BaseModel):
    reason: Reason


class RemoveRecordaResponse(BaseModel):
    recorda_id: UUID
    deleted_at: datetime
    resolved_reports: int
