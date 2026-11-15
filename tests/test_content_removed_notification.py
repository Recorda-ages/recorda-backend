"""Contrato da US42; integração com o endpoint da #87 ainda depende dele."""

from datetime import timedelta

from sqlalchemy import func, select

from app.core.time import now_utc
from app.models import ModerationAction, Notification, Recorda
from app.models.moderation_action import (
    ACTION_CHANGE_REPORT_STATUS,
    ACTION_REMOVE_RECORDA,
)
from app.models.notification import TYPE_CONTENT_REMOVED
from app.services import moderation_service, notification_service
from tests.factories import (
    add_moderation_action,
    add_notification,
    add_recorda,
    auth_headers,
)

URL = "/api/v1/notifications"


def test_notice_is_pending_until_the_caller_commits(db, common_user):
    recorda = add_recorda(db, common_user)
    notice = notification_service.notify_content_removed(db, recorda)
    assert notice.recipient_id == common_user.user_id
    assert notice.sender_id is None
    assert notice.recorda_id == recorda.recorda_id
    assert notice.type == TYPE_CONTENT_REMOVED
    assert notice.is_read is False
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_removal_audit_and_notice_roll_back_together(db, common_user, admin_user):
    recorda = add_recorda(db, common_user)
    recorda.deleted_at = now_utc()
    moderation_service.record_action(
        db,
        admin=admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda_id=recorda.recorda_id,
        target_user_id=common_user.user_id,
        reason="Conteúdo impróprio",
    )
    notification_service.notify_content_removed(db, recorda)
    db.rollback()
    assert db.get(Recorda, recorda.recorda_id).deleted_at is None
    assert db.scalar(select(func.count()).select_from(ModerationAction)) == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_deleted_recorda_notice_returns_latest_removal_only(
    client, db, common_user, admin_user
):
    recorda = add_recorda(db, common_user, deleted_at=now_utc())
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=recorda,
        reason="Motivo anterior",
        created_at=now_utc() - timedelta(days=1),
    )
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=recorda,
        reason="Motivo final",
    )
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_CHANGE_REPORT_STATUS,
        target_recorda=recorda,
        reason="Outra ação mais recente",
    )
    other_recorda = add_recorda(db, admin_user)
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=other_recorda,
        reason="Outra Recorda",
    )
    notification_service.notify_content_removed(db, recorda)
    db.commit()
    add_notification(
        db, common_user, "LIKE", sender=admin_user, recorda_id=recorda.recorda_id
    )

    response = client.get(URL, headers=auth_headers(common_user))
    assert response.status_code == 200
    body = response.json()
    assert body["unread_count"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["type"] == TYPE_CONTENT_REMOVED
    assert item["recorda_id"] == str(recorda.recorda_id)
    assert item["removal_reason"] == "Motivo final"
    assert item["recorda_song_title"] == recorda.song_title
    assert item["sender"] is None
    assert str(admin_user.user_id) not in response.text
    assert "admin_id" not in item


def test_other_types_do_not_receive_removal_fields(client, db, common_user, admin_user):
    recorda = add_recorda(db, common_user)
    add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_recorda=recorda,
        reason="Motivo",
    )
    add_notification(
        db, common_user, "LIKE", sender=admin_user, recorda_id=recorda.recorda_id
    )
    item = client.get(URL, headers=auth_headers(common_user)).json()["items"][0]
    assert item["removal_reason"] is None
    assert item["recorda_song_title"] is None


def test_missing_audit_returns_null_reason(client, db, common_user):
    recorda = add_recorda(db, common_user, deleted_at=now_utc())
    notification_service.notify_content_removed(db, recorda)
    db.commit()
    item = client.get(URL, headers=auth_headers(common_user)).json()["items"][0]
    assert item["removal_reason"] is None
    assert item["recorda_song_title"] == recorda.song_title


def test_pagination_read_all_and_recipient_isolation(
    client, db, common_user, admin_user
):
    recorda = add_recorda(db, common_user, deleted_at=now_utc())
    for days in range(3):
        add_moderation_action(
            db,
            admin_user,
            action_type=ACTION_REMOVE_RECORDA,
            target_recorda=recorda,
            created_at=now_utc() - timedelta(days=days),
        )
    notice = notification_service.notify_content_removed(db, recorda)
    db.commit()
    notice_id = str(notice.notification_id)
    other_recorda = add_recorda(db, admin_user, deleted_at=now_utc())
    notification_service.notify_content_removed(db, other_recorda)
    db.commit()
    headers = auth_headers(common_user)
    page = client.get(URL, params={"limit": 1}, headers=headers).json()
    assert [item["notification_id"] for item in page["items"]] == [notice_id]
    assert page["unread_count"] == 1
    assert (
        client.get(URL, params={"limit": 1, "offset": 1}, headers=headers).json()[
            "items"
        ]
        == []
    )
    assert client.post(f"{URL}/read-all", headers=headers).status_code == 204
    page = client.get(URL, headers=headers).json()
    assert page["unread_count"] == 0
    assert page["items"][0]["is_read"] is True
    assert client.get(URL, headers=auth_headers(admin_user)).json()["unread_count"] == 1


def test_author_deletion_does_not_create_removal_notice(client, db, common_user):
    recorda = add_recorda(db, common_user)
    response = client.delete(
        f"/api/v1/recordas/{recorda.recorda_id}", headers=auth_headers(common_user)
    )
    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Notification)) == 0
