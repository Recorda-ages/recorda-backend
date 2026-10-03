"""record_action: validação do motivo e fronteira transacional."""

import pytest
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import ModerationAction, Recorda
from app.models.moderation_action import (
    ACTION_REMOVE_RECORDA,
    ACTION_SUSPEND_USER,
)
from app.services import moderation_service
from app.services.moderation_service import MAX_REASON_LENGTH, InvalidReasonError
from tests.factories import add_recorda, add_user

# --------------------------------------------------------------------------- #
# Validação do motivo obrigatório (D-02 / D-04)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("reason", ["", "   ", "\n\t "])
def test_empty_reason_is_rejected(db: Session, reason: str):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    with pytest.raises(InvalidReasonError):
        moderation_service.record_action(
            db,
            admin=admin,
            action_type=ACTION_SUSPEND_USER,
            reason=reason,
            target_user_id=target.user_id,
        )

    assert db.query(ModerationAction).count() == 0


def test_reason_above_the_limit_is_rejected(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    with pytest.raises(InvalidReasonError):
        moderation_service.record_action(
            db,
            admin=admin,
            action_type=ACTION_SUSPEND_USER,
            reason="x" * (MAX_REASON_LENGTH + 1),
            target_user_id=target.user_id,
        )

    assert db.query(ModerationAction).count() == 0


def test_reason_at_the_limit_is_accepted(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_SUSPEND_USER,
        reason="x" * MAX_REASON_LENGTH,
        target_user_id=target.user_id,
    )

    assert len(action.reason) == MAX_REASON_LENGTH


def test_reason_is_stripped_before_persisting(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_SUSPEND_USER,
        reason="   Discurso de ódio   ",
        target_user_id=target.user_id,
    )
    db.commit()

    assert action.reason == "Discurso de ódio"


def test_reason_whose_length_only_fits_after_strip_is_accepted(db: Session):
    """O limite vale para o motivo já normalizado, não para o texto cru."""
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_SUSPEND_USER,
        reason="  " + "x" * MAX_REASON_LENGTH + "  ",
        target_user_id=target.user_id,
    )

    assert len(action.reason) == MAX_REASON_LENGTH


# --------------------------------------------------------------------------- #
# Registro da ação
# --------------------------------------------------------------------------- #


def test_record_action_persists_admin_target_and_details(db: Session):
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    details = {"target_type": "RECORDA", "report_count": 2}

    action = moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_REMOVE_RECORDA,
        reason="Conteúdo inadequado",
        target_recorda_id=recorda.recorda_id,
        target_user_id=author.user_id,
        details=details,
    )
    db.commit()

    assert action.admin_id == admin.user_id
    assert action.action_type == ACTION_REMOVE_RECORDA
    assert action.target_recorda_id == recorda.recorda_id
    assert action.target_user_id == author.user_id
    assert action.details == details
    assert action.created_at is not None


def test_record_action_does_not_commit(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_SUSPEND_USER,
        reason="Spam reiterado",
        target_user_id=target.user_id,
    )
    db.rollback()

    assert db.query(ModerationAction).count() == 0


# --------------------------------------------------------------------------- #
# Atomicidade: a mudança de estado e a auditoria vivem na mesma transação
# --------------------------------------------------------------------------- #


def test_rollback_discards_both_the_state_change_and_the_audit_row(db: Session):
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    recorda.deleted_at = now_utc()
    moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_REMOVE_RECORDA,
        reason="Conteúdo inadequado",
        target_recorda_id=recorda.recorda_id,
        target_user_id=author.user_id,
    )
    db.rollback()

    assert db.get(Recorda, recorda.recorda_id).deleted_at is None
    assert db.query(ModerationAction).count() == 0


def test_commit_persists_both_the_state_change_and_the_audit_row(db: Session):
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    recorda.deleted_at = now_utc()
    moderation_service.record_action(
        db,
        admin=admin,
        action_type=ACTION_REMOVE_RECORDA,
        reason="Conteúdo inadequado",
        target_recorda_id=recorda.recorda_id,
        target_user_id=author.user_id,
    )
    db.commit()

    assert db.get(Recorda, recorda.recorda_id).deleted_at is not None
    assert db.query(ModerationAction).count() == 1


def test_a_failed_audit_does_not_leave_the_state_change_behind(db: Session):
    """Motivo inválido aborta a auditoria; o service chamador faz rollback e a
    remoção não sobrevive — não há estado alterado sem auditoria."""
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    recorda.deleted_at = now_utc()
    with pytest.raises(InvalidReasonError):
        moderation_service.record_action(
            db,
            admin=admin,
            action_type=ACTION_REMOVE_RECORDA,
            reason="   ",
            target_recorda_id=recorda.recorda_id,
            target_user_id=author.user_id,
        )
    db.rollback()

    assert db.get(Recorda, recorda.recorda_id).deleted_at is None
    assert db.query(ModerationAction).count() == 0
