"""Acceptance tests for the administrative removal of a Recorda."""

import uuid

import pytest
from sqlalchemy import select

from app.core.time import now_utc
from app.models import ModerationAction, RecordaLike
from app.models.moderation_action import ACTION_REMOVE_RECORDA
from app.models.report import STATUS_DISMISSED, STATUS_OPEN, STATUS_RESOLVED
from app.services import moderation_service
from tests.factories import (
    add_comment,
    add_follow,
    add_recorda,
    add_report,
    add_user,
    auth_headers,
)

REASON = "Conteúdo impróprio"
ALREADY_REMOVED_MESSAGE = "Esta Recorda já foi removida."
MARKER = "Removed By Admin Song"


def remove_url(recorda_id) -> str:
    return f"/api/v1/admin/recordas/{recorda_id}/remove"


def remove(client, admin, recorda_id, reason=REASON):
    return client.post(
        remove_url(recorda_id), json={"reason": reason}, headers=auth_headers(admin)
    )


def moderation_actions(db) -> list[ModerationAction]:
    return list(db.scalars(select(ModerationAction)))


def test_remove_recorda_soft_deletes_and_returns_summary(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "author"))

    response = remove(client, admin_user, recorda.recorda_id)

    assert response.status_code == 200
    body = response.json()
    assert body["recorda_id"] == str(recorda.recorda_id)
    assert body["deleted_at"]
    assert body["resolved_reports"] == 0
    db.refresh(recorda)
    assert recorda.deleted_at is not None


def test_remove_recorda_resolves_only_open_reports_of_that_recorda(
    client, db, admin_user
):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    other_recorda = add_recorda(db, author, song_title="Outra")
    open_a = add_report(db, add_user(db, "reporter_a"), recorda=recorda)
    open_b = add_report(db, add_user(db, "reporter_b"), recorda=recorda)
    dismissed = add_report(
        db, add_user(db, "reporter_c"), recorda=recorda, status=STATUS_DISMISSED
    )
    unrelated = add_report(db, add_user(db, "reporter_d"), recorda=other_recorda)

    response = remove(client, admin_user, recorda.recorda_id)

    assert response.status_code == 200
    assert response.json()["resolved_reports"] == 2
    for report in (open_a, open_b, dismissed, unrelated):
        db.refresh(report)
    assert open_a.status == STATUS_RESOLVED
    assert open_b.status == STATUS_RESOLVED
    assert open_a.resolved_at is not None
    assert open_b.resolved_at is not None
    assert dismissed.status == STATUS_DISMISSED
    assert unrelated.status == STATUS_OPEN
    assert unrelated.resolved_at is None


def test_remove_recorda_records_exactly_one_audit_action(client, db, admin_user):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    add_report(db, add_user(db, "reporter"), recorda=recorda)

    response = remove(client, admin_user, recorda.recorda_id, reason=f"  {REASON}  ")

    assert response.status_code == 200
    (action,) = moderation_actions(db)
    assert action.action_type == ACTION_REMOVE_RECORDA
    assert action.admin_id == admin_user.user_id
    assert action.target_user_id == author.user_id
    assert action.target_recorda_id == recorda.recorda_id
    assert action.reason == REASON
    assert action.details == {"resolved_reports": 1}


def test_remove_recorda_cleans_likes_and_comments_like_author_delete(
    client, db, admin_user
):
    author = add_user(db, "author")
    fan = add_user(db, "fan")
    recorda = add_recorda(db, author)
    db.add(RecordaLike(user_id=fan.user_id, recorda_id=recorda.recorda_id))
    db.commit()
    comment = add_comment(db, fan, recorda)

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    assert db.get(RecordaLike, (fan.user_id, recorda.recorda_id)) is None
    db.refresh(comment)
    assert comment.deleted_at is not None


def test_remove_recorda_twice_returns_409(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "author"))
    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    response = remove(client, admin_user, recorda.recorda_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert response.json()["error"]["message"] == ALREADY_REMOVED_MESSAGE
    assert len(moderation_actions(db)) == 1


def test_remove_recorda_already_deleted_by_author_returns_409(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "author"), deleted_at=now_utc())

    response = remove(client, admin_user, recorda.recorda_id)

    assert response.status_code == 409
    assert moderation_actions(db) == []


def test_remove_recorda_missing_returns_404(client, admin_user):
    response = remove(client, admin_user, uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_remove_recorda_rejects_invalid_reason(client, db, admin_user, reason):
    recorda = add_recorda(db, add_user(db, "author"))

    response = remove(client, admin_user, recorda.recorda_id, reason=reason)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    db.refresh(recorda)
    assert recorda.deleted_at is None
    assert moderation_actions(db) == []


def test_remove_recorda_requires_reason_field(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "author"))

    response = client.post(
        remove_url(recorda.recorda_id), json={}, headers=auth_headers(admin_user)
    )

    assert response.status_code == 422


def test_remove_recorda_accepts_reason_of_500_characters(client, db, admin_user):
    recorda = add_recorda(db, add_user(db, "author"))

    assert remove(client, admin_user, recorda.recorda_id, "x" * 500).status_code == 200


def test_remove_recorda_requires_admin(client, db, common_user):
    recorda = add_recorda(db, add_user(db, "author"))

    response = remove(client, common_user, recorda.recorda_id)

    assert response.status_code == 403
    db.refresh(recorda)
    assert recorda.deleted_at is None


def test_remove_recorda_requires_auth(client, db):
    recorda = add_recorda(db, add_user(db, "author"))

    response = client.post(remove_url(recorda.recorda_id), json={"reason": REASON})

    assert response.status_code == 401


def test_audit_failure_rolls_back_the_removal(client, db, admin_user, monkeypatch):
    author = add_user(db, "author")
    fan = add_user(db, "fan")
    recorda = add_recorda(db, author)
    report = add_report(db, add_user(db, "reporter"), recorda=recorda)
    db.add(RecordaLike(user_id=fan.user_id, recorda_id=recorda.recorda_id))
    db.commit()
    comment = add_comment(db, fan, recorda)

    def failing_record_action(*args, **kwargs):
        raise RuntimeError("falha na auditoria")

    monkeypatch.setattr(moderation_service, "record_action", failing_record_action)

    with pytest.raises(RuntimeError, match="falha na auditoria"):
        remove(client, admin_user, recorda.recorda_id)

    db.refresh(recorda)
    db.refresh(report)
    db.refresh(comment)
    assert recorda.deleted_at is None
    assert report.status == STATUS_OPEN
    assert report.resolved_at is None
    assert comment.deleted_at is None
    assert db.get(RecordaLike, (fan.user_id, recorda.recorda_id)) is not None
    assert moderation_actions(db) == []


READS = [
    pytest.param("/api/v1/feed/following", id="feed-following"),
    pytest.param("/api/v1/recordas", id="recordas-list"),
]


@pytest.mark.parametrize("url", READS)
def test_removed_recorda_disappears_from_user_reads(client, db, admin_user, url):
    author = add_user(db, "author")
    viewer = add_user(db, "viewer")
    add_follow(db, viewer, author)
    recorda = add_recorda(db, author, song_title=MARKER)
    headers = auth_headers(viewer)

    def appears() -> bool:
        response = client.get(url, headers=headers)
        assert response.status_code == 200, response.text
        return str(recorda.recorda_id) in response.text or MARKER in response.text

    assert appears(), "a Recorda deveria aparecer antes da remoção"

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    assert not appears(), "a Recorda ainda aparece depois da remoção"


def test_removed_recorda_leaves_author_profile_count(client, db, admin_user):
    author = add_user(
        db,
        "author",
        fav_song_deezer_track_id="3135556",
        fav_song_title="Song of Silence",
        fav_song_artist_name="Disturbed",
        fav_song_cover_url="https://e.deezer.com/cover.jpg",
    )
    recorda = add_recorda(db, author)
    headers = auth_headers(author)

    def recordas_count() -> int:
        response = client.get("/api/v1/users/me/profile", headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["counts"]["recordas"]

    assert recordas_count() == 1

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    assert recordas_count() == 0


def test_removed_recorda_detail_returns_404(client, db, admin_user):
    author = add_user(db, "author")
    viewer = add_user(db, "viewer")
    recorda = add_recorda(db, author)
    url = f"/api/v1/recordas/{recorda.recorda_id}"
    assert client.get(url, headers=auth_headers(viewer)).status_code == 200

    assert remove(client, admin_user, recorda.recorda_id).status_code == 200

    assert client.get(url, headers=auth_headers(viewer)).status_code == 404
    assert client.get(url, headers=auth_headers(author)).status_code == 404
