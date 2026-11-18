"""US 42: o autor é avisado quando a moderação remove uma Recorda."""

import pytest
from sqlalchemy import func, select

from app.models import ModerationAction, Notification, Recorda
from app.models.app_user import STATUS_SUSPENDED
from app.models.moderation_action import ACTION_REMOVE_RECORDA
from app.models.notification import TYPE_CONTENT_REMOVED
from app.services import notification_service
from tests.factories import (
    add_moderation_action,
    add_notification,
    add_recorda,
    add_user,
    auth_headers,
)

URL = "/api/v1/notifications"
REASON = "Conteúdo impróprio"


def remove(client, admin, recorda_id, reason=REASON):
    return client.post(
        f"/api/v1/admin/recordas/{recorda_id}/removal",
        json={"reason": reason},
        headers=auth_headers(admin),
    )


def notification_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Notification))


def test_admin_removal_notifies_author_with_reason_and_song(
    client, db, common_user, admin_user
):
    recorda = add_recorda(db, common_user, song_title="Removed Song")

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    response = client.get(URL, headers=auth_headers(common_user))
    assert response.status_code == 200
    body = response.json()
    assert body["unread_count"] == 1
    (item,) = body["items"]
    assert item["type"] == TYPE_CONTENT_REMOVED
    assert item["removal_reason"] == REASON
    assert item["recorda_song_title"] == "Removed Song"
    assert item["sender"] is None
    assert item["recorda_id"] is None
    assert item["recorda_media_url"] is None
    assert str(admin_user.user_id) not in response.text
    assert "admin_id" not in item


def test_removal_notice_is_not_visible_to_the_admin(
    client, db, common_user, admin_user
):
    recorda = add_recorda(db, common_user)

    remove(client, admin_user, recorda.recorda_id)

    page = client.get(URL, headers=auth_headers(admin_user)).json()
    assert page == {"items": [], "unread_count": 0}


def test_repeated_removal_does_not_create_another_notice(
    client, db, common_user, admin_user
):
    recorda = add_recorda(db, common_user)

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200
    assert remove(client, admin_user, recorda.recorda_id).status_code == 409

    assert notification_count(db) == 1


def test_suspended_author_is_not_notified(client, db, admin_user):
    author = add_user(db, "suspended_author", status=STATUS_SUSPENDED)
    recorda = add_recorda(db, author)

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    assert notification_count(db) == 0
    assert db.scalar(select(func.count()).select_from(ModerationAction)) == 1


def test_notice_is_pending_until_the_caller_commits(db, common_user, admin_user):
    action = add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_user=common_user,
        reason=REASON,
    )

    notice = notification_service.notify_content_removed(db, common_user, action)

    assert notice.recipient_id == common_user.user_id
    assert notice.sender_id is None
    assert notice.moderation_action_id == action.action_id
    assert notice.type == TYPE_CONTENT_REMOVED
    assert notice.is_read is False
    db.rollback()
    assert notification_count(db) == 0


def test_failed_removal_rolls_back_the_notice(
    client, db, common_user, admin_user, monkeypatch
):
    recorda = add_recorda(db, common_user)

    def fail(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(notification_service, "notify_content_removed", fail)

    with pytest.raises(RuntimeError):
        remove(client, admin_user, recorda.recorda_id)

    assert notification_count(db) == 0
    assert db.scalar(select(func.count()).select_from(ModerationAction)) == 0
    assert db.get(Recorda, recorda.recorda_id) is not None


def test_missing_song_title_in_audit_returns_null(client, db, common_user, admin_user):
    action = add_moderation_action(
        db,
        admin_user,
        action_type=ACTION_REMOVE_RECORDA,
        target_user=common_user,
        reason=REASON,
    )
    notification_service.notify_content_removed(db, common_user, action)
    db.commit()

    (item,) = client.get(URL, headers=auth_headers(common_user)).json()["items"]
    assert item["removal_reason"] == REASON
    assert item["recorda_song_title"] is None


def test_other_types_do_not_receive_removal_fields(client, db, common_user, admin_user):
    recorda = add_recorda(db, common_user)
    add_notification(
        db, common_user, "LIKE", sender=admin_user, recorda_id=recorda.recorda_id
    )

    (item,) = client.get(URL, headers=auth_headers(common_user)).json()["items"]
    assert item["removal_reason"] is None
    assert item["recorda_song_title"] is None


def test_pagination_read_all_and_recipient_isolation(
    client, db, common_user, admin_user
):
    other_author = add_user(db, "other_author")
    remove(client, admin_user, add_recorda(db, common_user).recorda_id)
    remove(client, admin_user, add_recorda(db, other_author).recorda_id)
    headers = auth_headers(common_user)

    page = client.get(URL, params={"limit": 1}, headers=headers).json()
    assert len(page["items"]) == 1
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
    other_page = client.get(URL, headers=auth_headers(other_author)).json()
    assert other_page["unread_count"] == 1


def test_author_deletion_does_not_create_removal_notice(client, db, common_user):
    recorda = add_recorda(db, common_user)
    response = client.delete(
        f"/api/v1/recordas/{recorda.recorda_id}", headers=auth_headers(common_user)
    )
    assert response.status_code == 204
    assert notification_count(db) == 0
