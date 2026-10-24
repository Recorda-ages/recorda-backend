"""Fila de moderação: denúncias agrupadas por alvo (T-E10.US44.BE.01)."""

from uuid import UUID

from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models.report import (
    STATUS_DISMISSED,
    STATUS_OPEN,
    STATUS_RESOLVED,
    TARGET_RECORDA,
    TARGET_USER,
)
from app.repositories import recorda_repository, report_repository, user_repository
from app.repositories.report_repository import GroupOrder
from app.schemas.moderation import AdminSummary
from app.schemas.recorda import RecordaRead
from app.schemas.report import (
    ReportAuthor,
    ReportDetail,
    ReportGroup,
    ReportGroupDetail,
    ReportGroupPage,
    ReportRecordaTarget,
    ReportTargetPreview,
    ReportUserTarget,
)
from app.services import moderation_service
from app.services.report_preview_service import PreviewKey, load_target_previews

# Statuses that are considered "closed" and can be bulk-resolved or bulk-dismissed.
_CLOSED_STATUSES = (STATUS_RESOLVED, STATUS_DISMISSED)


class NoReportsForTargetError(Exception):
    """The administrative detail exists only for reported targets."""


def get_detail(db: Session, *, target_type: str, target_id: UUID) -> ReportGroupDetail:
    rows = report_repository.list_for_target(
        db, target_type=target_type, target_id=target_id
    )
    if not rows:
        raise NoReportsForTargetError

    if target_type == TARGET_RECORDA:
        recorda = recorda_repository.get_by_id_including_deleted(db, target_id)
        author = user_repository.get_by_id_including_deleted(db, recorda.user_id)
        # Reports retain their targets through non-cascading foreign keys.
        # Administrative reads deliberately bypass viewer visibility rules.
        target = ReportRecordaTarget(
            **RecordaRead.model_validate(recorda).model_dump(),
            deleted_at=recorda.deleted_at,
            author=ReportAuthor.model_validate(author),
        )
    else:
        user = user_repository.get_by_id_including_deleted(db, target_id)
        target = ReportUserTarget.model_validate(user)
    return ReportGroupDetail(
        target_type=target_type,
        target=target,
        reports=[
            ReportDetail(
                report_id=row.Report.report_id,
                reporter=AdminSummary(
                    user_id=row.Report.reporter_id, username=row.reporter_username
                ),
                description=row.Report.description,
                status=row.Report.status,
                created_at=row.Report.created_at,
                resolved_at=row.Report.resolved_at,
            )
            for row in rows
        ],
        actions=moderation_service.list_target_actions(
            db, target_type=target_type, target_id=target_id
        ),
    )


def list_groups(
    db: Session,
    *,
    target_type: str | None,
    status: str,
    order: GroupOrder,
    limit: int,
    offset: int,
) -> ReportGroupPage:
    rows = report_repository.list_groups(
        db,
        target_type=target_type,
        status=status,
        order=order,
        limit=limit,
        offset=offset,
    )
    previews = _load_previews(db, rows)

    return ReportGroupPage(
        items=[_to_group(row, previews) for row in rows],
        total=report_repository.count_groups(
            db, target_type=target_type, status=status
        ),
    )


def resolve_open_reports(
    db: Session,
    *,
    target_type: str,
    target_id: UUID,
    new_status: str,
) -> int:
    """Muda o status em lote das denúncias de um alvo **sem commit**.

    - Para RESOLVED ou DISMISSED: afeta todas as denúncias OPEN do alvo.
      Preenche `resolved_at` com o instante atual (UTC).
    - Para OPEN (reabrir): afeta todas as denúncias RESOLVED/DISMISSED do alvo.
      Limpa `resolved_at`. Não restaura conteúdo removido nem reativa conta;
      para isso existem as ações próprias (REMOVE_RECORDA, SUSPEND_USER).

    Retorna a contagem de linhas afetadas. Retorna 0 sem tocar no banco se
    nenhuma denúncia estiver no estado de origem esperado.

    Reutilizado por T-E10.US45.BE.01 e T-E10.US46.BE.02.
    """
    if new_status == STATUS_OPEN:
        from_statuses = _CLOSED_STATUSES
        resolved_at = None
    else:
        from_statuses = (STATUS_OPEN,)
        resolved_at = now_utc()

    recorda_id = target_id if target_type == TARGET_RECORDA else None
    reported_user_id = target_id if target_type == TARGET_USER else None

    return report_repository.bulk_update_status(
        db,
        recorda_id=recorda_id,
        reported_user_id=reported_user_id,
        from_statuses=from_statuses,
        new_status=new_status,
        resolved_at=resolved_at,
    )


def _load_previews(
    db: Session, rows: list[Row]
) -> dict[PreviewKey, ReportTargetPreview]:
    recorda_ids = {row.target_id for row in rows if row.target_type == TARGET_RECORDA}
    user_ids = {row.target_id for row in rows if row.target_type == TARGET_USER}
    return load_target_previews(db, user_ids=user_ids, recorda_ids=recorda_ids)


def _to_group(row: Row, previews: dict[PreviewKey, ReportTargetPreview]) -> ReportGroup:
    return ReportGroup(
        target_type=row.target_type,
        target_id=row.target_id,
        status=row.status,
        report_count=row.report_count,
        first_reported_at=row.first_reported_at,
        last_reported_at=row.last_reported_at,
        preview=previews[(row.target_type, row.target_id)],
    )
