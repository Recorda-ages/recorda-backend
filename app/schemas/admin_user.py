from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.moderation import ModerationActionType
from app.schemas.report import ReportTargetPreview

AdminUserRole = Literal["USER", "ADMIN"]
AdminUserStatus = Literal["ACTIVE", "SUSPENDED"]
AdminReportTarget = Literal["USER", "RECORDA"]
AdminReportStatus = Literal["OPEN", "RESOLVED", "DISMISSED"]


class AdminUserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    name: str
    email: str
    profile_picture_url: str | None
    role: AdminUserRole
    status: AdminUserStatus
    reports_count: int
    deleted_at: datetime | None = None


class AdminUserPage(BaseModel):
    items: list[AdminUserRow]
    total: int


class AdminUserReportGroup(BaseModel):
    target_type: AdminReportTarget
    target_id: UUID
    status: AdminReportStatus
    report_count: int
    first_reported_at: datetime
    last_reported_at: datetime
    preview: ReportTargetPreview | None = None


class AdminUserAction(BaseModel):
    action_id: UUID
    action_type: ModerationActionType
    admin_id: UUID
    admin_username: str
    target_user_id: UUID | None = None
    target_recorda_id: UUID | None = None
    reason: str
    details: dict[str, Any] | None = None
    created_at: datetime


class AdminUserDetail(AdminUserRow):
    created_at: datetime
    is_private: bool
    recordas_count: int
    reports_received: list[AdminUserReportGroup]
    actions: list[AdminUserAction]