"""Acesso de persistência da trilha de auditoria de moderação.

Append-only: só há inserção e leitura. Não existe `save`, `update` nem
`delete` — uma ação já registrada nunca é alterada (no PostgreSQL um
trigger recusa UPDATE e DELETE).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.app_user import AppUser
from app.models.moderation_action import ModerationAction
from app.models.recorda import Recorda
from app.models.report import TARGET_RECORDA

Admin = aliased(AppUser)
TargetUser = aliased(AppUser)
RecordaAuthor = aliased(AppUser)


def add(db: Session, action: ModerationAction) -> ModerationAction:
    """Registra a ação sem commit (commit feito pelo service).

    O `flush` popula `action_id` e dispara as constraints ainda dentro da
    transação da operação que está sendo auditada.
    """
    db.add(action)
    db.flush()
    return action


def _matching(q: str):
    """Ações cujo admin, usuário alvo, Recorda alvo (título ou autor) ou motivo contém `q`.

    Subconsultas em vez de joins: `_with_labels` já faz os joins da listagem.
    """
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    users = select(AppUser.user_id).where(AppUser.username.ilike(pattern, escape="\\"))
    recordas = select(Recorda.recorda_id).where(
        or_(
            Recorda.song_title.ilike(pattern, escape="\\"),
            Recorda.user_id.in_(users),
        )
    )
    return or_(
        ModerationAction.admin_id.in_(users),
        ModerationAction.target_user_id.in_(users),
        ModerationAction.target_recorda_id.in_(recordas),
        ModerationAction.reason.ilike(pattern, escape="\\"),
    )


def _filtered(
    *,
    admin_id: UUID | None,
    action_type: str | None,
    created_from: datetime | None,
    created_before: datetime | None,
    q: str | None = None,
) -> Select:
    statement = select(ModerationAction)
    if q:
        statement = statement.where(_matching(q))
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
    q: str | None = None,
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
        q=q,
    )
    page = _with_labels(filtered).limit(limit).offset(offset)
    total = filtered.with_only_columns(func.count(ModerationAction.action_id))

    return list(db.execute(page).all()), db.execute(total).scalar_one()


def list_for_target(db: Session, *, target_type: str, target_id: UUID) -> list[Row]:
    """Complete history for the target, including deleted admins and content."""
    target_column = (
        ModerationAction.target_recorda_id
        if target_type == TARGET_RECORDA
        else ModerationAction.target_user_id
    )
    statement = select(ModerationAction).where(target_column == target_id)
    return list(db.execute(_with_labels(statement)).all())


def _with_labels(statement: Select) -> Select:
    return (
        statement.join(Admin, ModerationAction.admin_id == Admin.user_id)
        .outerjoin(TargetUser, ModerationAction.target_user_id == TargetUser.user_id)
        .outerjoin(Recorda, ModerationAction.target_recorda_id == Recorda.recorda_id)
        .outerjoin(RecordaAuthor, Recorda.user_id == RecordaAuthor.user_id)
        .add_columns(
            Admin.username.label("admin_username"),
            TargetUser.username.label("target_username"),
            Recorda.song_title.label("target_song_title"),
            RecordaAuthor.username.label("target_recorda_author"),
        )
        .order_by(
            ModerationAction.created_at.desc(),
            ModerationAction.action_id.desc(),
        )
    )
