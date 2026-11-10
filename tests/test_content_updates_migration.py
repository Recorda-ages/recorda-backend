"""Verify physical deletion with historical IDs in a migrated PostgreSQL."""

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError

from app.models import (
    ModerationAction,
    Notification,
    Recorda,
    RecordaComment,
    RecordaMention,
    Report,
)
from app.models.notification import TYPE_MENTION
from app.services import recorda_service
from tests.factories import (
    add_comment,
    add_moderation_action,
    add_recorda,
    add_report,
    add_user,
)

pytestmark = pytest.mark.postgres


def test_migration_preserves_historical_ids_and_immutable_audit(pg_db):
    author, friend, admin = (
        add_user(pg_db, "author"),
        add_user(pg_db, "friend"),
        add_user(pg_db, "admin"),
    )
    recorda = add_recorda(pg_db, author)
    recorda_id = recorda.recorda_id
    comment = add_comment(pg_db, friend, recorda)
    comment_id = comment.comment_id
    report = add_report(pg_db, friend, recorda=recorda)
    report_id = report.report_id
    action = add_moderation_action(pg_db, admin, target_recorda=recorda)
    action_id = action.action_id
    pg_db.add(RecordaMention(recorda_id=recorda_id, user_id=friend.user_id))
    pg_db.add(
        Notification(
            recipient_id=friend.user_id,
            sender_id=author.user_id,
            recorda_id=recorda_id,
            type=TYPE_MENTION,
        )
    )
    pg_db.commit()
    assert recorda_service.delete(pg_db, recorda_id, author)
    assert pg_db.get(Recorda, recorda_id) is None
    assert pg_db.get(RecordaComment, comment_id) is None
    assert pg_db.scalar(select(RecordaMention)) is None
    assert pg_db.scalar(select(Notification)) is None
    assert pg_db.get(Report, report_id).recorda_id == recorda_id
    assert pg_db.get(ModerationAction, action_id).target_recorda_id == recorda_id
    assert not any(
        fk["constrained_columns"] == ["recorda_id"]
        for fk in inspect(pg_db.bind).get_foreign_keys("report")
    )
    with pytest.raises(DBAPIError):
        pg_db.execute(
            text("DELETE FROM moderation_action WHERE action_id = :id"),
            {"id": action_id},
        )
    pg_db.rollback()
    assert pg_db.get(ModerationAction, action_id) is not None
