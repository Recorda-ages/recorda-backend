"""Regras de negócio da trilha de auditoria de moderação."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.app_user import AppUser
from app.models.moderation_action import ModerationAction
from app.repositories import moderation_action_repository

MAX_REASON_LENGTH = 500


class InvalidReasonError(Exception):
    """Motivo da ação administrativa ausente ou acima do limite (D-04)."""


def record_action(
    db: Session,
    *,
    admin: AppUser,
    action_type: str,
    reason: str,
    target_user_id: UUID | None = None,
    target_recorda_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> ModerationAction:
    """Registra uma ação administrativa **sem commit**.

    O commit é do service da operação auditada, para que a mudança de estado
    e a auditoria caiam na mesma transação: não há estado alterado sem
    auditoria, nem auditoria de algo que não aconteceu.
    """
    reason = reason.strip() if reason else ""
    if not reason:
        raise InvalidReasonError("O motivo da ação é obrigatório.")
    if len(reason) > MAX_REASON_LENGTH:
        raise InvalidReasonError(
            f"O motivo da ação não pode passar de {MAX_REASON_LENGTH} caracteres."
        )

    return moderation_action_repository.add(
        db,
        ModerationAction(
            admin_id=admin.user_id,
            action_type=action_type,
            target_user_id=target_user_id,
            target_recorda_id=target_recorda_id,
            reason=reason,
            details=details,
        ),
    )
