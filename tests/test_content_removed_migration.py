"""Upgrade e downgrade reais do CHECK, em PostgreSQL descartável."""

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.core.config import settings
from app.models import Notification
from app.services import notification_service
from tests.conftest import TEST_DATABASE_URL, requires_postgres
from tests.factories import add_notification, add_recorda, add_user

pytestmark = requires_postgres


def test_upgrade_and_downgrade_preserve_social_notifications(pg_db):
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
    pg_db.rollback()
    config = Config("alembic.ini")
    previous_url = settings.database_url
    settings.database_url = TEST_DATABASE_URL
    try:
        command.downgrade(config, "0008_moderation_action")
        notifications = list(pg_db.scalars(select(Notification)))
        assert [notice.notification_id for notice in notifications] == [social_id]
        pg_db.rollback()
        with pytest.raises(IntegrityError):
            add_notification(
                pg_db, author, "CONTENT_REMOVED", recorda_id=recorda.recorda_id
            )
        pg_db.rollback()
        command.upgrade(config, "head")
        notice = add_notification(
            pg_db, author, "CONTENT_REMOVED", recorda_id=recorda.recorda_id
        )
        assert notice.type == "CONTENT_REMOVED"
    finally:
        settings.database_url = previous_url
