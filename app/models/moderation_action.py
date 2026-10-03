"""Trilha de auditoria imutável das ações administrativas de moderação."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
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

ACTION_REMOVE_RECORDA = "REMOVE_RECORDA"
ACTION_CHANGE_REPORT_STATUS = "CHANGE_REPORT_STATUS"
ACTION_SUSPEND_USER = "SUSPEND_USER"
ACTION_REACTIVATE_USER = "REACTIVATE_USER"

MODERATION_ACTION_TYPES = (
    ACTION_REMOVE_RECORDA,
    ACTION_CHANGE_REPORT_STATUS,
    ACTION_SUSPEND_USER,
    ACTION_REACTIVATE_USER,
)

_ACTION_TYPE_LIST = ", ".join(f"'{value}'" for value in MODERATION_ACTION_TYPES)

# Pelo menos um alvo — não exatamente um, ao contrário de `ck_report_single_target`:
# REMOVE_RECORDA preenche os dois (a Recorda e o autor dela), para que o histórico
# administrativo por usuário saia de `target_user_id` sem join com `recorda`.
_HAS_TARGET = "target_user_id IS NOT NULL OR target_recorda_id IS NOT NULL"


class ModerationAction(Base):
    """Append-only: nunca sofre UPDATE nem DELETE.

    A imutabilidade é imposta no PostgreSQL por trigger (migration
    `0008_moderation_action`), e por isso a tabela não tem `updated_at`
    nem `deleted_at`.
    """

    __tablename__ = "moderation_action"
    __table_args__ = (
        CheckConstraint(
            f"action_type IN ({_ACTION_TYPE_LIST})", name="ck_moderation_action_type"
        ),
        CheckConstraint(_HAS_TARGET, name="ck_moderation_action_has_target"),
        Index("ix_moderation_action_created_at", text("created_at DESC")),
        Index(
            "ix_moderation_action_admin_id_created_at",
            "admin_id",
            text("created_at DESC"),
        ),
        Index("ix_moderation_action_target_user_id", "target_user_id"),
        Index("ix_moderation_action_target_recorda_id", "target_recorda_id"),
    )

    action_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.user_id"), nullable=True
    )
    target_recorda_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
