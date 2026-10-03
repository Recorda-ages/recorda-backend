"""Imutabilidade de moderation_action — exige PostgreSQL.

O trigger `trg_moderation_action_immutable` é criado pela migration
`0008_moderation_action` e só existe no PostgreSQL. O SQLite da suíte não tem
equivalente, então estes testes são skipados quando `TEST_DATABASE_URL` não
está definida (é o caso do CI atual).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models import ModerationAction
from app.models.moderation_action import ACTION_SUSPEND_USER
from tests.conftest import requires_postgres

IMMUTABLE_MESSAGE = "moderation_action é imutável"

pytestmark = requires_postgres


@pytest.fixture
def recorded_action(pg_db: Session) -> ModerationAction:
    """Um admin, um alvo e uma ação já registrada e commitada."""
    pg_db.execute(
        text(
            "INSERT INTO app_user "
            "(user_id, username, email, name, language, is_private, role, status,"
            " created_at, updated_at) VALUES "
            "(:admin, 'admin_mod', 'admin@e.com', 'Admin', 'pt-BR', false,"
            " 'ADMIN', 'ACTIVE', now(), now()), "
            "(:target, 'alvo', 'alvo@e.com', 'Alvo', 'pt-BR', false,"
            " 'USER', 'ACTIVE', now(), now())"
        ),
        {
            "admin": uuid.UUID("11111111-1111-1111-1111-111111111111"),
            "target": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        },
    )
    action = ModerationAction(
        admin_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        action_type=ACTION_SUSPEND_USER,
        target_user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        reason="Spam reiterado",
    )
    pg_db.add(action)
    pg_db.commit()
    return action


def test_update_is_blocked_by_the_trigger(
    pg_db: Session, recorded_action: ModerationAction
):
    with pytest.raises(ProgrammingError) as error:
        pg_db.execute(
            text(
                "UPDATE moderation_action SET reason = 'alterado' WHERE action_id = :i"
            ),
            {"i": recorded_action.action_id},
        )

    assert IMMUTABLE_MESSAGE in str(error.value)
    pg_db.rollback()
    assert pg_db.get(ModerationAction, recorded_action.action_id).reason == (
        "Spam reiterado"
    )


def test_delete_is_blocked_by_the_trigger(
    pg_db: Session, recorded_action: ModerationAction
):
    with pytest.raises(ProgrammingError) as error:
        pg_db.execute(
            text("DELETE FROM moderation_action WHERE action_id = :i"),
            {"i": recorded_action.action_id},
        )

    assert IMMUTABLE_MESSAGE in str(error.value)
    pg_db.rollback()
    assert pg_db.get(ModerationAction, recorded_action.action_id) is not None


def test_bulk_update_is_blocked_by_the_trigger(
    pg_db: Session, recorded_action: ModerationAction
):
    """O trigger é FOR EACH ROW: pega UPDATE sem WHERE do mesmo jeito."""
    with pytest.raises(ProgrammingError) as error:
        pg_db.execute(text("UPDATE moderation_action SET reason = 'alterado'"))

    assert IMMUTABLE_MESSAGE in str(error.value)
    pg_db.rollback()


def test_bulk_delete_is_blocked_by_the_trigger(
    pg_db: Session, recorded_action: ModerationAction
):
    with pytest.raises(ProgrammingError) as error:
        pg_db.execute(text("DELETE FROM moderation_action"))

    assert IMMUTABLE_MESSAGE in str(error.value)
    pg_db.rollback()
    assert pg_db.query(ModerationAction).count() == 1


def test_insert_is_still_allowed(pg_db: Session, recorded_action: ModerationAction):
    """A trilha é append-only, não read-only."""
    pg_db.add(
        ModerationAction(
            admin_id=recorded_action.admin_id,
            action_type=ACTION_SUSPEND_USER,
            target_user_id=recorded_action.target_user_id,
            reason="Outra ação",
        )
    )
    pg_db.commit()

    assert pg_db.query(ModerationAction).count() == 2
