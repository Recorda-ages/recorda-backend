"""Acesso de persistência da trilha de auditoria de moderação.

Append-only: só há inserção e leitura. Não existe `save`, `update` nem
`delete` — uma ação já registrada nunca é alterada (no PostgreSQL um
trigger recusa UPDATE e DELETE).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.moderation_action import ModerationAction


def add(db: Session, action: ModerationAction) -> ModerationAction:
    """Registra a ação sem commit (commit feito pelo service).

    O `flush` popula `action_id` e dispara as constraints ainda dentro da
    transação da operação que está sendo auditada.
    """
    db.add(action)
    db.flush()
    return action


def list_recent(db: Session, *, limit: int, offset: int) -> list[ModerationAction]:
    statement = (
        select(ModerationAction)
        .order_by(
            ModerationAction.created_at.desc(),
            ModerationAction.action_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))
