"""Constraints da tabela moderation_action e funções do repository."""

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AppUser, ModerationAction, Recorda
from app.models.moderation_action import (
    ACTION_CHANGE_REPORT_STATUS,
    ACTION_REACTIVATE_USER,
    ACTION_REMOVE_RECORDA,
    ACTION_SUSPEND_USER,
    MODERATION_ACTION_TYPES,
)
from app.repositories import moderation_action_repository
from tests.factories import add_moderation_action, add_recorda, add_user

# --------------------------------------------------------------------------- #
# Constraints
# --------------------------------------------------------------------------- #


def test_the_four_action_types_are_accepted(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    for action_type in MODERATION_ACTION_TYPES:
        add_moderation_action(db, admin, action_type=action_type, target_user=target)

    assert db.query(ModerationAction).count() == len(MODERATION_ACTION_TYPES) == 4


def test_action_type_outside_the_vocabulary_is_rejected(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    with pytest.raises(IntegrityError):
        add_moderation_action(
            db, admin, action_type="DELETE_EVERYTHING", target_user=target
        )


def test_action_without_any_target_is_rejected(db: Session):
    admin = add_user(db, "admin_mod")

    with pytest.raises(IntegrityError):
        add_moderation_action(db, admin, action_type=ACTION_SUSPEND_USER)


def test_action_with_only_a_user_target_is_accepted(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = add_moderation_action(
        db, admin, action_type=ACTION_SUSPEND_USER, target_user=target
    )

    assert action.target_user_id == target.user_id
    assert action.target_recorda_id is None


def test_action_with_only_a_recorda_target_is_accepted(db: Session):
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    action = add_moderation_action(
        db, admin, action_type=ACTION_CHANGE_REPORT_STATUS, target_recorda=recorda
    )

    assert action.target_recorda_id == recorda.recorda_id
    assert action.target_user_id is None


def test_remove_recorda_may_fill_both_targets(db: Session):
    """`ck_moderation_action_has_target` exige PELO MENOS um alvo, não exatamente
    um: REMOVE_RECORDA grava a Recorda e o autor dela (histórico da US46)."""
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)

    action = add_moderation_action(
        db,
        admin,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=recorda,
        target_user=author,
    )

    assert action.target_recorda_id == recorda.recorda_id
    assert action.target_user_id == author.user_id


def test_reason_is_mandatory(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    with pytest.raises(IntegrityError):
        add_moderation_action(db, admin, target_user=target, reason=None)


def test_details_round_trips_as_json(db: Session):
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    details = {
        "from": "OPEN",
        "to": "DISMISSED",
        "report_count": 3,
        "target_type": "RECORDA",
    }

    action = add_moderation_action(
        db,
        admin,
        action_type=ACTION_CHANGE_REPORT_STATUS,
        target_recorda=recorda,
        details=details,
    )
    db.expire_all()

    assert db.get(ModerationAction, action.action_id).details == details


def test_details_is_optional(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = add_moderation_action(db, admin, target_user=target, details=None)

    assert action.details is None


# --------------------------------------------------------------------------- #
# Hard delete: as FKs sem `ondelete` bloqueiam a exclusão física do registro
# referenciado, preservando a trilha. Um teste por relação.
# --------------------------------------------------------------------------- #


def test_hard_delete_of_the_admin_is_blocked_by_admin_id(db: Session):
    """Relação exercitada: moderation_action.admin_id -> app_user.user_id."""
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")
    add_moderation_action(db, admin, target_user=target)

    with pytest.raises(IntegrityError):
        db.execute(delete(AppUser).where(AppUser.user_id == admin.user_id))
        db.commit()


def test_hard_delete_of_the_target_user_is_blocked_by_target_user_id(db: Session):
    """Relação exercitada: moderation_action.target_user_id -> app_user.user_id."""
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")
    add_moderation_action(db, admin, target_user=target)

    with pytest.raises(IntegrityError):
        db.execute(delete(AppUser).where(AppUser.user_id == target.user_id))
        db.commit()


def test_hard_delete_of_the_target_recorda_is_blocked_by_target_recorda_id(
    db: Session,
):
    """Relação: moderation_action.target_recorda_id -> recorda.recorda_id."""
    admin = add_user(db, "admin_mod")
    author = add_user(db, "autor")
    recorda = add_recorda(db, author)
    add_moderation_action(
        db, admin, action_type=ACTION_REMOVE_RECORDA, target_recorda=recorda
    )

    with pytest.raises(IntegrityError):
        db.execute(delete(Recorda).where(Recorda.recorda_id == recorda.recorda_id))
        db.commit()


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


def test_add_does_not_commit(db: Session):
    """A transação é do service: depois de `add`, um rollback descarta tudo."""
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    moderation_action_repository.add(
        db,
        ModerationAction(
            admin_id=admin.user_id,
            action_type=ACTION_SUSPEND_USER,
            target_user_id=target.user_id,
            reason="Spam reiterado",
        ),
    )
    db.rollback()

    assert db.query(ModerationAction).count() == 0


def test_add_flushes_so_the_pk_is_available_before_commit(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")

    action = moderation_action_repository.add(
        db,
        ModerationAction(
            admin_id=admin.user_id,
            action_type=ACTION_REACTIVATE_USER,
            target_user_id=target.user_id,
            reason="Suspensão revista",
        ),
    )

    assert action.action_id is not None
    db.commit()
    assert db.query(ModerationAction).count() == 1


def test_list_recent_orders_by_created_at_desc(db: Session):
    from datetime import timedelta

    from app.core.time import now_utc

    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")
    base = now_utc()

    older = add_moderation_action(
        db, admin, target_user=target, reason="antiga", created_at=base - timedelta(2)
    )
    newer = add_moderation_action(
        db, admin, target_user=target, reason="recente", created_at=base
    )
    middle = add_moderation_action(
        db, admin, target_user=target, reason="meio", created_at=base - timedelta(1)
    )

    rows = moderation_action_repository.list_recent(db, limit=10, offset=0)

    assert [row.action_id for row in rows] == [
        newer.action_id,
        middle.action_id,
        older.action_id,
    ]


def test_list_recent_paginates(db: Session):
    admin = add_user(db, "admin_mod")
    target = add_user(db, "alvo")
    for index in range(5):
        add_moderation_action(db, admin, target_user=target, reason=f"motivo {index}")

    first = moderation_action_repository.list_recent(db, limit=2, offset=0)
    second = moderation_action_repository.list_recent(db, limit=2, offset=2)

    assert len(first) == len(second) == 2
    assert {a.action_id for a in first}.isdisjoint({a.action_id for a in second})
