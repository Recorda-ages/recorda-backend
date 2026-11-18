"""Upgrade e downgrade reais do CHECK, em PostgreSQL descartável."""

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import settings
from app.models import Notification
from app.services import notification_service
from tests.factories import add_notification, add_recorda, add_user

pytestmark = pytest.mark.postgres


def test_upgrade_and_downgrade_preserve_social_notifications(pg_db, pg_database_url):
    author = add_user(pg_db, "author")
    recorda = add_recorda(pg_db, author)
    social = add_notification(pg_db, author, "MENTION", recorda_id=recorda.recorda_id)
    social_id = social.notification_id
    add_notification(pg_db, author, "CONTENT_REMOVED", recorda_id=recorda.recorda_id)
    page = notification_service.list_notifications(
        pg_db, author.user_id, limit=20, offset=0
    )
    assert page.unread_count == 2
    removal = next(item for item in page.items if item.type == "CONTENT_REMOVED")
    assert removal.recorda_song_title == recorda.song_title
    assert removal.removal_reason is None
    assert removal.sender is None

    check = next(
        constraint
        for constraint in inspect(pg_db.bind).get_check_constraints("notification")
        if constraint["name"] == "ck_notification_type"
    )
    assert "CONTENT_REMOVED" in check["sqltext"]
    recorda_id = recorda.recorda_id  # capture before session is closed
    author_id = author.user_id
    pg_db.close()  # release connection so Alembic DDL is not blocked by our lock
    config = Config("alembic.ini")
    previous_url = settings.database_url
    settings.database_url = pg_database_url
    try:
        command.downgrade(config, "0008_moderation_action")
        notification_ids = list(pg_db.scalars(select(Notification.notification_id)))
        assert notification_ids == [social_id]
        pg_db.rollback()
        with pytest.raises(IntegrityError):
            pg_db.execute(
                text(
                    "INSERT INTO notification "
                    "(notification_id, recipient_id, recorda_id, type) "
                    "VALUES (gen_random_uuid(), :recipient, :recorda, "
                    "'CONTENT_REMOVED')"
                ),
                {"recipient": author_id, "recorda": recorda_id},
            )
        pg_db.rollback()
        command.upgrade(config, "head")
        notice = add_notification(
            pg_db, author, "CONTENT_REMOVED", recorda_id=recorda_id
        )
        assert notice.type == "CONTENT_REMOVED"
    finally:
        settings.database_url = previous_url
