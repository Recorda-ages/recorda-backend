"""Moderation report opened by a user against exactly one target."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

STATUS_OPEN = "OPEN"
STATUS_RESOLVED = "RESOLVED"
STATUS_DISMISSED = "DISMISSED"

REPORT_STATUSES = (
    STATUS_OPEN,
    STATUS_RESOLVED,
    STATUS_DISMISSED,
)

TARGET_RECORDA = "RECORDA"
TARGET_USER = "USER"

_STATUS_LIST = ", ".join(f"'{value}'" for value in REPORT_STATUSES)

# num_nonnulls() is PostgreSQL-only; this CASE sum is equivalent and also runs
# on the SQLite used by the test suite.
_SINGLE_TARGET = """(CASE WHEN reported_user_id IS NOT NULL THEN 1 ELSE 0 END
 + CASE WHEN recorda_id IS NOT NULL THEN 1 ELSE 0 END
 + CASE WHEN comment_id IS NOT NULL THEN 1 ELSE 0 END) = 1"""


class Report(Base):
    __tablename__ = "report"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_LIST})", name="ck_report_status"),
        CheckConstraint(_SINGLE_TARGET, name="ck_report_single_target"),
        Index(
            "uq_report_reporter_recorda",
            "reporter_id",
            "recorda_id",
            unique=True,
            postgresql_where=text("recorda_id IS NOT NULL"),
            sqlite_where=text("recorda_id IS NOT NULL"),
        ),
        Index(
            "uq_report_reporter_user",
            "reporter_id",
            "reported_user_id",
            unique=True,
            postgresql_where=text("reported_user_id IS NOT NULL"),
            sqlite_where=text("reported_user_id IS NOT NULL"),
        ),
        Index(
            "ix_report_status_created_at",
            "status",
            text("created_at DESC"),
        ),
        Index("ix_report_recorda_id", "recorda_id"),
        Index("ix_report_reported_user_id", "reported_user_id"),
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=False
    )
    reported_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=True
    )
    recorda_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id"), nullable=True
    )
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("recorda_comment.comment_id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=STATUS_OPEN, server_default=STATUS_OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
