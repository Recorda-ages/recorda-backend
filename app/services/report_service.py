"""Regras de negócio das denúncias de Recorda."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda, Report
from app.models.report import STATUS_OPEN
from app.repositories import report_repository
from app.schemas.report import ReportCreate
from app.services import recorda_service


class ReportTargetNotFoundError(Exception):
    """A Recorda não existe, foi excluída ou o autor não está ativo."""


class ReportAccessDeniedError(Exception):
    """O denunciante não pode ver a Recorda (conta privada sem vínculo ACCEPTED)."""


class SelfReportError(Exception):
    """O usuário tentou denunciar a própria Recorda."""


class DuplicateReportError(Exception):
    """O usuário já denunciou esta Recorda."""


def report_recorda(
    db: Session, recorda_id: UUID, reporter: AppUser, payload: ReportCreate
) -> Report:
    """Abre uma denúncia OPEN contra a Recorda.

    A denúncia só entra na fila de moderação: a Recorda continua visível
    e o autor não é notificado.
    """
    recorda = _get_reportable_recorda(db, recorda_id, reporter)
    _ensure_not_reported_yet(
        db, reporter_id=reporter.user_id, recorda_id=recorda.recorda_id
    )

    report = Report(
        reporter_id=reporter.user_id,
        recorda_id=recorda.recorda_id,
        description=payload.description,
        status=STATUS_OPEN,
    )
    return _add_or_raise_duplicate(db, report)


def _get_reportable_recorda(
    db: Session, recorda_id: UUID, reporter: AppUser
) -> Recorda:
    try:
        recorda = recorda_service.get_viewable_recorda(db, recorda_id, reporter)
    except recorda_service.RecordaAccessDeniedError as exc:
        raise ReportAccessDeniedError from exc

    if recorda is None:
        raise ReportTargetNotFoundError
    if recorda.user_id == reporter.user_id:
        raise SelfReportError
    return recorda


def _ensure_not_reported_yet(
    db: Session, *, reporter_id: UUID, recorda_id: UUID
) -> None:
    if report_repository.exists_for_recorda(
        db, reporter_id=reporter_id, recorda_id=recorda_id
    ):
        raise DuplicateReportError


def _add_or_raise_duplicate(db: Session, report: Report) -> Report:
    reporter_id, recorda_id = report.reporter_id, report.recorda_id
    try:
        return report_repository.add(db, report)
    except IntegrityError as exc:
        db.rollback()
        # Duas requisições simultâneas podem passar juntas pela checagem prévia;
        # quem decide é o índice único uq_report_reporter_recorda. Outra violação
        # de integridade não é duplicidade e deve subir.
        if report_repository.exists_for_recorda(
            db, reporter_id=reporter_id, recorda_id=recorda_id
        ):
            raise DuplicateReportError from exc
        raise
