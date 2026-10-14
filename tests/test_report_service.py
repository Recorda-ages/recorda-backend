"""Casos do report_service que a rota não alcança."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Report
from app.repositories import report_repository
from app.schemas.report import ReportCreate
from app.services import report_service
from tests.factories import add_recorda, add_report, add_user


def _skip_prior_check(*_args, **_kwargs) -> None:
    """Simula a corrida: a checagem prévia ainda não enxerga a outra denúncia."""


def test_concurrent_duplicate_is_raised_as_duplicate_report(db, monkeypatch):
    reporter = add_user(db, "denunciante")
    recorda = add_recorda(db, add_user(db, "autor"))
    add_report(db, reporter, recorda=recorda)
    monkeypatch.setattr(report_service, "_ensure_not_reported_yet", _skip_prior_check)

    with pytest.raises(report_service.DuplicateReportError):
        report_service.report_recorda(db, recorda.recorda_id, reporter, ReportCreate())

    assert len(db.scalars(select(Report)).all()) == 1


def test_other_integrity_error_is_not_masked_as_duplicate(db, monkeypatch):
    reporter = add_user(db, "denunciante")
    recorda = add_recorda(db, add_user(db, "autor"))

    def _failing_add(_db, _report):
        raise IntegrityError("INSERT INTO report", {}, Exception("outra constraint"))

    monkeypatch.setattr(report_repository, "add", _failing_add)

    with pytest.raises(IntegrityError):
        report_service.report_recorda(db, recorda.recorda_id, reporter, ReportCreate())
