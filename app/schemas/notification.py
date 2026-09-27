from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

NotificationType = Literal[
    "FOLLOW_REQUEST",
    "FOLLOW_ACCEPTED",
    "NEW_FOLLOWER",
    "LIKE",
    "COMMENT",
    "MENTION",
]


class NotificationSender(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    profile_picture_url: str | None = None


class NotificationItem(BaseModel):
    notification_id: UUID
    type: NotificationType
    is_read: bool
    created_at: datetime

    sender: NotificationSender | None = None

    recorda_id: UUID | None = None
    comment_id: UUID | None = None
    follow_id: UUID | None = None


class NotificationPage(BaseModel):
    items: list[NotificationItem]
    unread_count: int
