"""Regression coverage for removal, mentions and missing song genres."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import (
    ModerationAction,
    Notification,
    Recorda,
    RecordaComment,
    RecordaMention,
    Report,
)
from app.models.notification import TYPE_COMMENT, TYPE_MENTION
from app.repositories import retrospective_repository
from app.services import (
    comment_service,
    genre_backfill_service,
    recorda_service,
)
from tests.factories import (
    DEEZER_ROUTES,
    add_comment,
    add_follow,
    add_moderation_action,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
    deezer_stub,
)
from tests.test_recorda_routes import create_payload

URL = "/api/v1/recordas"


def test_tagging_persists_deduplicates_notifies_and_reads(client, db):
    owner, friend = add_user(db, "owner"), add_user(db, "friend")
    add_follow(db, owner, friend)
    response = client.post(
        URL,
        json=create_payload(mentioned_user_ids=[str(friend.user_id)] * 2),
        headers=auth_headers(owner),
    )
    assert response.status_code == 201
    recorda_id = response.json()["recorda_id"]
    assert db.scalar(select(func.count()).select_from(RecordaMention)) == 1
    notification = db.scalar(
        select(Notification).where(Notification.type == TYPE_MENTION)
    )
    assert notification.recipient_id == friend.user_id
    detail = client.get(f"{URL}/{recorda_id}", headers=auth_headers(friend)).json()
    assert detail["mentioned_users"][0]["username"] == "friend"
    from uuid import UUID

    assert (
        retrospective_repository.top_tagged_users(db, [UUID(recorda_id)])[0][
            "tag_count"
        ]
        == 1
    )
    client.delete(f"{URL}/{recorda_id}", headers=auth_headers(owner))
    assert db.scalar(select(func.count()).select_from(RecordaMention)) == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


@pytest.mark.parametrize(
    "kind",
    ["unknown", "self", "stranger", "deleted", "suspended", "pending", "cannot-view"],
)
def test_invalid_tags_do_not_publish_or_notify(client, db, kind):
    owner = add_user(db, "owner", is_private=(kind == "cannot-view"))
    target = add_user(
        db,
        "target",
        status="SUSPENDED" if kind == "suspended" else "ACTIVE",
        deleted_at=datetime.now(UTC) if kind == "deleted" else None,
    )
    if kind in ("deleted", "suspended", "pending", "cannot-view"):
        add_follow(
            db, owner, target, status="PENDING" if kind == "pending" else "ACCEPTED"
        )
    target_id = (
        uuid4()
        if kind == "unknown"
        else owner.user_id
        if kind == "self"
        else target.user_id
    )
    response = client.post(
        URL,
        json=create_payload(mentioned_user_ids=[str(target_id)]),
        headers=auth_headers(owner),
    )
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(Recorda)) == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_deleted_tagged_accounts_disappear_from_detail_and_retrospective(client, db):
    owner, friend = add_user(db, "owner"), add_user(db, "friend")
    recorda = add_recorda(db, owner)
    db.add(RecordaMention(recorda_id=recorda.recorda_id, user_id=friend.user_id))
    friend.deleted_at = datetime.now(UTC)
    db.commit()
    assert (
        client.get(f"{URL}/{recorda.recorda_id}", headers=auth_headers(owner)).json()[
            "mentioned_users"
        ]
        == []
    )
    assert retrospective_repository.top_tagged_users(db, [recorda.recorda_id]) == []


def test_physical_removal_preserves_reports_audit_and_admin_reads(client, db):
    owner, reporter, admin = (
        add_user(db, "owner"),
        add_user(db, "reporter"),
        add_user(db, "admin", role="ADMIN"),
    )
    recorda = add_recorda(db, owner)
    recorda_id = recorda.recorda_id
    report = add_report(db, reporter, recorda=recorda)
    action = add_moderation_action(db, admin, target_recorda=recorda)
    assert recorda_service.delete(db, recorda_id, owner)
    db.expire_all()
    assert db.get(Recorda, recorda_id) is None
    assert db.get(Report, report.report_id).recorda_id == recorda_id
    assert db.get(ModerationAction, action.action_id).target_recorda_id == recorda_id
    from app.services import admin_report_service

    result = admin_report_service.get_detail(
        db, target_type="RECORDA", target_id=recorda_id
    )
    assert result.target.removed is True
    assert result.target.recorda_id == recorda_id
    groups = admin_report_service.list_groups(
        db, target_type="RECORDA", status="OPEN", order="oldest", limit=20, offset=0
    )
    assert groups.items[0].preview.title == "Conteúdo removido"


def test_delete_comment_removes_notifications_and_keeps_report(db):
    owner, friend = add_user(db, "owner"), add_user(db, "friend")
    recorda = add_recorda(db, owner)
    comment = add_comment(db, friend, recorda)
    comment_id = comment.comment_id
    report = Report(reporter_id=owner.user_id, comment_id=comment_id)
    db.add(report)
    db.add(
        Notification(
            recipient_id=owner.user_id,
            sender_id=friend.user_id,
            recorda_id=recorda.recorda_id,
            comment_id=comment_id,
            type=TYPE_COMMENT,
        )
    )
    db.commit()
    assert comment_service.delete(db, comment_id, friend)
    assert db.get(RecordaComment, comment_id) is None
    assert db.get(Report, report.report_id).comment_id == comment_id
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


def test_genre_id_fallback_and_backfill_only_missing_live_rows(db):
    owner = add_user(db, "owner")
    missing1, missing2 = add_recorda(db, owner), add_recorda(db, owner)
    known = add_recorda(db, owner, song_genre_name="Rock")
    deleted = add_recorda(db, owner, deleted_at=datetime.now(UTC))
    client = deezer_stub(
        {
            **DEEZER_ROUTES,
            "/album/302127": {"genre_id": 106},
            "/genre/106": {"id": 106, "name": "Electro"},
        }
    )
    assert genre_backfill_service.backfill_genres(db, client) == (1, 2)
    assert missing1.song_genre_name == missing2.song_genre_name == "Electro"
    assert known.song_genre_name == "Rock"
    assert deleted.song_genre_name is None
    assert genre_backfill_service.backfill_genres(db, client) == (0, 0)


def test_genre_backfill_can_retry_unavailable_track(db):
    owner = add_user(db, "owner")
    recorda = add_recorda(db, owner)
    assert genre_backfill_service.backfill_genres(db, deezer_stub()) == (1, 0)
    assert recorda.song_genre_name is None
    assert genre_backfill_service.backfill_genres(db, deezer_stub(DEEZER_ROUTES)) == (
        1,
        1,
    )
