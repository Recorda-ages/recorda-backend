"""Acesso de persistência da trilha de auditoria de moderação.

Append-only: só há inserção e leitura. Não existe `save`, `update` nem
`delete` — uma ação já registrada nunca é alterada (no PostgreSQL um
trigger recusa UPDATE e DELETE).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session, aliased

from app.models.app_user import AppUser
from app.models.moderation_action import ModerationAction
from app.models.recorda import Recorda

Admin = aliased(AppUser)
TargetUser = aliased(AppUser)


def add(db: Session, action: ModerationAction) -> ModerationAction:
    """Registra a ação sem commit (commit feito pelo service).

    O `flush` popula `action_id` e dispara as constraints ainda dentro da
    transação da operação que está sendo auditada.
    """
    db.add(action)
    db.flush()
    return action


def _filtered(
    *,
    admin_id: UUID | None,
    action_type: str | None,
    created_from: datetime | None,
    created_before: datetime | None,
) -> Select:
    statement = select(ModerationAction)
    if admin_id is not None:
        statement = statement.where(ModerationAction.admin_id == admin_id)
    if action_type is not None:
        statement = statement.where(ModerationAction.action_type == action_type)
    if created_from is not None:
        statement = statement.where(ModerationAction.created_at >= created_from)
    if created_before is not None:
        statement = statement.where(ModerationAction.created_at < created_before)
    return statement


def search(
    db: Session,
    *,
    admin_id: UUID | None = None,
    action_type: str | None = None,
    created_from: datetime | None = None,
    created_before: datetime | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Row], int]:
    """Página filtrada do log, com os nomes de admin e alvo, e o total sem paginação.

    Os joins não filtram `deleted_at`: a auditoria continua legível depois que
    o admin, o usuário ou a Recorda alvo são excluídos.
    """
    filtered = _filtered(
        admin_id=admin_id,
        action_type=action_type,
        created_from=created_from,
        created_before=created_before,
    )
    page = (
        filtered.join(Admin, ModerationAction.admin_id == Admin.user_id)
        .outerjoin(TargetUser, ModerationAction.target_user_id == TargetUser.user_id)
        .outerjoin(Recorda, ModerationAction.target_recorda_id == Recorda.recorda_id)
        .add_columns(
            Admin.username.label("admin_username"),
            TargetUser.username.label("target_username"),
            Recorda.song_title.label("target_song_title"),
        )
        .order_by(
            ModerationAction.created_at.desc(),
            ModerationAction.action_id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    total = filtered.with_only_columns(func.count(ModerationAction.action_id))

    return list(db.execute(page).all()), db.execute(total).scalar_one()
