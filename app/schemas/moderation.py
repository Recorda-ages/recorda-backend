from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ModerationActionType = Literal[
    "REMOVE_RECORDA",
    "CHANGE_REPORT_STATUS",
    "SUSPEND_USER",
    "REACTIVATE_USER",
]


class AdminSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str


class AuditEntry(BaseModel):
    """Uma ação administrativa: quem, qual ação, sobre qual alvo, quando e por quê."""

    action_id: UUID
    action_type: ModerationActionType
    admin: AdminSummary
    target_user_id: UUID | None = None
    target_recorda_id: UUID | None = None
    target_label: str
    reason: str
    details: dict[str, Any] | None = None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditEntry]
    total: int
