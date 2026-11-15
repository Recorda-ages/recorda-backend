"""Regras de negócio das denúncias de Recorda e Perfil"""

from collections.abc import Callable
from functools import partial
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda, Report
from app.models.app_user import STATUS_ACTIVE
from app.models.report import STATUS_OPEN
from app.repositories import report_repository, user_repository
from app.schemas.report import ReportCreate
from app.services import recorda_service


class ReportTargetNotFoundError(Exception):
    """O alvo não existe, foi excluído ou não está ativo."""


class ReportAccessDeniedError(Exception):
    """O denunciante não pode ver a Recorda (conta privada sem vínculo ACCEPTED)."""


class SelfReportError(Exception):
    """O usuário tentou denunciar a si mesmo ou a própria Recorda."""


class DuplicateReportError(Exception):
    """O usuário já denunciou este alvo."""


def report_recorda(
    db: Session, recorda_id: UUID, reporter: AppUser, payload: ReportCreate
) -> Report:
    """Abre uma denúncia OPEN contra a Recorda.

    A denúncia só entra na fila de moderação: a Recorda continua visível
    e o autor não é notificado.
    """
    recorda = _get_reportable_recorda(db, recorda_id, reporter)
    already_reported = partial(
        report_repository.exists_for_recorda,
        db,
        reporter_id=reporter.user_id,
        recorda_id=recorda.recorda_id,
    )
    _ensure_not_reported_yet(already_reported)

    report = Report(
        reporter_id=reporter.user_id,
        recorda_id=recorda.recorda_id,
        description=payload.description,
        status=STATUS_OPEN,
    )
    return _add_or_raise_duplicate(db, report, already_reported)


def report_user(
    db: Session, user_id: UUID, reporter: AppUser, payload: ReportCreate
) -> Report:
    """Abre uma denúncia OPEN contra o perfil.

    Perfil privado pode ser denunciado sem seguir, pois aparece na busca.
    O denunciado não é notificado.
    """
    target = _get_reportable_user(db, user_id, reporter)
    already_reported = partial(
        report_repository.exists_for_user,
        db,
        reporter_id=reporter.user_id,
        reported_user_id=target.user_id,
    )
    _ensure_not_reported_yet(already_reported)

    report = Report(
        reporter_id=reporter.user_id,
        reported_user_id=target.user_id,
        description=payload.description,
        status=STATUS_OPEN,
    )
    return _add_or_raise_duplicate(db, report, already_reported)


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


def _get_reportable_user(db: Session, user_id: UUID, reporter: AppUser) -> AppUser:
    # get_by_id já ignora contas excluídas; suspensa também vira 404
    # para não expor o estado da conta.
    target = user_repository.get_by_id(db, user_id)
    if target is None or target.status != STATUS_ACTIVE:
        raise ReportTargetNotFoundError
    if target.user_id == reporter.user_id:
        raise SelfReportError
    return target


AlreadyReported = Callable[[], bool]


def _ensure_not_reported_yet(already_reported: AlreadyReported) -> None:
    if already_reported():
        raise DuplicateReportError


def _add_or_raise_duplicate(
    db: Session, report: Report, already_reported: AlreadyReported
) -> Report:
    try:
        return report_repository.add(db, report)
    except IntegrityError as exc:
        db.rollback()
        # Duas requisições simultâneas podem passar juntas pela checagem prévia;
        # quem decide é o índice único do alvo. Outra violação de integridade
        # não é duplicidade e deve subir.
        if already_reported():
            raise DuplicateReportError from exc
        raise
