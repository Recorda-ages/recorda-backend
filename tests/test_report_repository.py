"""Constraints da tabela report e funções do report_repository."""

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppUser, Recorda, Report
from app.models.report import STATUS_OPEN
from app.repositories import report_repository
from tests.factories import add_comment, add_recorda, add_report, add_user

# --------------------------------------------------------------------------- #
# Constraints
# --------------------------------------------------------------------------- #


def test_report_without_any_target_is_rejected(db: Session):
    reporter = add_user(db, "denunciante")

    with pytest.raises(IntegrityError):
        add_report(db, reporter)


def test_report_with_two_targets_is_rejected(db: Session):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    with pytest.raises(IntegrityError):
        add_report(db, reporter, recorda=recorda, reported_user=author)


def test_report_against_a_comment_is_a_valid_single_target(db: Session):
    """`comment_id` é reservado (sem rota no MVP), mas vale como alvo único."""
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    comment = add_comment(db, author, recorda)

    report = report_repository.add(
        db, Report(reporter_id=reporter.user_id, comment_id=comment.comment_id)
    )

    assert report.comment_id == comment.comment_id
    assert report.status == STATUS_OPEN


def test_status_outside_the_vocabulary_is_rejected(db: Session):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    with pytest.raises(IntegrityError):
        add_report(db, reporter, recorda=recorda, status="UNDER_REVIEW")


def test_same_reporter_cannot_report_the_same_recorda_twice(db: Session):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    add_report(db, reporter, recorda=recorda)

    with pytest.raises(IntegrityError):
        add_report(db, reporter, recorda=recorda)


def test_same_reporter_can_report_different_recordas(db: Session):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    first = add_recorda(db, author)
    second = add_recorda(db, author)

    add_report(db, reporter, recorda=first)
    add_report(db, reporter, recorda=second)

    assert db.query(Report).count() == 2


def test_different_reporters_can_report_the_same_recorda(db: Session):
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    add_report(db, add_user(db, "denunciante_a"), recorda=recorda)
    add_report(db, add_user(db, "denunciante_b"), recorda=recorda)

    assert db.query(Report).count() == 2


def test_same_reporter_cannot_report_the_same_profile_twice(db: Session):
    reporter = add_user(db, "denunciante")
    target = add_user(db, "perfil_abusivo")
    add_report(db, reporter, reported_user=target)

    with pytest.raises(IntegrityError):
        add_report(db, reporter, reported_user=target)


def test_same_reporter_can_report_different_profiles(db: Session):
    reporter = add_user(db, "denunciante")

    add_report(db, reporter, reported_user=add_user(db, "perfil_a"))
    add_report(db, reporter, reported_user=add_user(db, "perfil_b"))

    assert db.query(Report).count() == 2


# --------------------------------------------------------------------------- #
# Hard delete: as FKs sem `ondelete` bloqueiam a exclusão física do
# registro referenciado, preservando a denúncia (nunca há cascata).
# Cada teste abaixo exercita uma relação diferente.
# --------------------------------------------------------------------------- #


def test_hard_delete_of_the_reporter_is_blocked_by_report_reporter_id(db: Session):
    """Relação exercitada: report.reporter_id -> app_user.user_id."""
    reporter = add_user(db, "denunciante")
    target = add_user(db, "perfil_abusivo")
    add_report(db, reporter, reported_user=target)

    with pytest.raises(IntegrityError):
        db.execute(delete(AppUser).where(AppUser.user_id == reporter.user_id))
        db.commit()


def test_hard_delete_of_the_reported_user_is_blocked_by_reported_user_id(db: Session):
    """Relação exercitada: report.reported_user_id -> app_user.user_id."""
    reporter = add_user(db, "denunciante")
    target = add_user(db, "perfil_abusivo")
    add_report(db, reporter, reported_user=target)

    with pytest.raises(IntegrityError):
        db.execute(delete(AppUser).where(AppUser.user_id == target.user_id))
        db.commit()


def test_hard_delete_of_the_reported_recorda_is_blocked_by_recorda_id(db: Session):
    """Relação exercitada: report.recorda_id -> recorda.recorda_id."""
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    add_report(db, reporter, recorda=recorda)

    with pytest.raises(IntegrityError):
        db.execute(delete(Recorda).where(Recorda.recorda_id == recorda.recorda_id))
        db.commit()


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


def test_add_persists_the_report_with_open_status_and_timestamp(db: Session):
    reporter = add_user(db, "denunciante")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    report = report_repository.add(
        db,
        Report(
            reporter_id=reporter.user_id,
            recorda_id=recorda.recorda_id,
            description="Conteúdo inadequado",
        ),
    )

    assert report.report_id is not None
    assert report.status == STATUS_OPEN
    assert report.created_at is not None
    assert report.resolved_at is None
    assert report.description == "Conteúdo inadequado"


def test_exists_for_recorda(db: Session):
    reporter = add_user(db, "denunciante")
    other = add_user(db, "outro")
    author = add_user(db, "autor")
    reported = add_recorda(db, author)
    untouched = add_recorda(db, author)
    add_report(db, reporter, recorda=reported)

    assert report_repository.exists_for_recorda(
        db, reporter_id=reporter.user_id, recorda_id=reported.recorda_id
    )
    assert not report_repository.exists_for_recorda(
        db, reporter_id=reporter.user_id, recorda_id=untouched.recorda_id
    )
    assert not report_repository.exists_for_recorda(
        db, reporter_id=other.user_id, recorda_id=reported.recorda_id
    )


def test_exists_for_user(db: Session):
    reporter = add_user(db, "denunciante")
    other = add_user(db, "outro")
    reported = add_user(db, "perfil_abusivo")
    untouched = add_user(db, "perfil_ok")
    add_report(db, reporter, reported_user=reported)

    assert report_repository.exists_for_user(
        db, reporter_id=reporter.user_id, reported_user_id=reported.user_id
    )
    assert not report_repository.exists_for_user(
        db, reporter_id=reporter.user_id, reported_user_id=untouched.user_id
    )
    assert not report_repository.exists_for_user(
        db, reporter_id=other.user_id, reported_user_id=reported.user_id
    )
