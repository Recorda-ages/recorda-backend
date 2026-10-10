"""Regras de negócio da trilha de auditoria de moderação."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.core.time import local_day_bounds
from app.models.app_user import AppUser
from app.models.moderation_action import ModerationAction
from app.repositories import moderation_action_repository, user_repository
from app.schemas.moderation import AdminSummary, AuditEntry, AuditLogPage

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


def list_audit_log(
    db: Session,
    *,
    admin_id: UUID | None = None,
    action_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int,
    offset: int,
) -> AuditLogPage:
    """Log de auditoria, do mais recente ao mais antigo.

    `date_from` e `date_to` são dias inclusivos no fuso de São Paulo: vão da
    meia-noite local de `date_from` até a meia-noite local seguinte a `date_to`.
    """
    created_from = local_day_bounds(date_from)[0] if date_from else None
    created_before = local_day_bounds(date_to)[1] if date_to else None

    rows, total = moderation_action_repository.search(
        db,
        admin_id=admin_id,
        action_type=action_type,
        created_from=created_from,
        created_before=created_before,
        limit=limit,
        offset=offset,
    )
    return AuditLogPage(items=[_to_entry(row) for row in rows], total=total)


def list_admins(db: Session) -> list[AdminSummary]:
    return [
        AdminSummary.model_validate(admin) for admin in user_repository.list_admins(db)
    ]


def _to_entry(row: Row) -> AuditEntry:
    action: ModerationAction = row.ModerationAction
    # REMOVE_RECORDA preenche os dois alvos; a Recorda é o alvo direto.
    target_label = row.target_song_title or row.target_username or ""

    return AuditEntry(
        action_id=action.action_id,
        action_type=action.action_type,
        admin=AdminSummary(user_id=action.admin_id, username=row.admin_username),
        target_user_id=action.target_user_id,
        target_recorda_id=action.target_recorda_id,
        target_label=target_label,
        reason=action.reason,
        details=action.details,
        created_at=action.created_at,
    )
