"""Acceptance tests for liking and unliking Recordas."""

import uuid

from sqlalchemy import func, select

from app.models import Follow, Notification, RecordaLike
from app.models.follow import STATUS_ACCEPTED
from app.models.notification import TYPE_LIKE
from tests.factories import add_recorda, add_user, auth_headers

PREFIX = "/api/v1/recordas"


def _count_likes(db, recorda_id) -> int:
    statement = (
        select(func.count())
        .select_from(RecordaLike)
        .where(RecordaLike.recorda_id == recorda_id)
    )
    return db.scalar(statement)


def test_liking_twice_does_not_duplicate_and_updates_count(client, db, common_user):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    headers = auth_headers(common_user)

    first = client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)
    second = client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)

    assert first.status_code == 200
    assert first.json() == {"likes_count": 1, "is_liked": True}
    assert second.status_code == 200
    assert second.json() == {"likes_count": 1, "is_liked": True}
    assert _count_likes(db, recorda.recorda_id) == 1


def test_other_user_like_creates_one_notification_for_author(client, db, common_user):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    headers = auth_headers(common_user)

    client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)
    client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)

    notifications = db.scalars(select(Notification)).all()
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient_id == author.user_id
    assert notification.sender_id == common_user.user_id
    assert notification.recorda_id == recorda.recorda_id
    assert notification.type == TYPE_LIKE
    assert notification.is_read is False


def test_liking_own_recorda_does_not_create_notification(client, db, common_user):
    recorda = add_recorda(db, common_user)

    response = client.post(
        f"{PREFIX}/{recorda.recorda_id}/likes",
        headers=auth_headers(common_user),
    )

    assert response.status_code == 200
    assert response.json() == {"likes_count": 1, "is_liked": True}
    assert db.scalars(select(Notification)).all() == []


def test_unliking_updates_count_immediately(client, db, common_user):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    headers = auth_headers(common_user)
    client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)

    response = client.delete(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"likes_count": 0, "is_liked": False}
    assert _count_likes(db, recorda.recorda_id) == 0


def test_unliking_does_not_remove_another_users_like(client, db, common_user):
    author = add_user(db, "author")
    other_user = add_user(db, "other")
    recorda = add_recorda(db, author)
    client.post(
        f"{PREFIX}/{recorda.recorda_id}/likes",
        headers=auth_headers(other_user),
    )

    response = client.delete(
        f"{PREFIX}/{recorda.recorda_id}/likes",
        headers=auth_headers(common_user),
    )

    assert response.status_code == 200
    assert response.json() == {"likes_count": 1, "is_liked": False}
    remaining_like = db.scalars(select(RecordaLike)).one()
    assert remaining_like.user_id == other_user.user_id


def test_feed_returns_count_and_current_user_like_state(client, db, common_user):
    author = add_user(db, "author")
    recorda = add_recorda(db, author)
    db.add(
        Follow(
            follower_id=common_user.user_id,
            following_id=author.user_id,
            status=STATUS_ACCEPTED,
        )
    )
    db.commit()
    headers = auth_headers(common_user)
    client.post(f"{PREFIX}/{recorda.recorda_id}/likes", headers=headers)

    response = client.get("/api/v1/feed/following", headers=headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["recorda_id"] == str(recorda.recorda_id)
    assert item["likes_count"] == 1
    assert item["is_liked"] is True


def test_like_and_unlike_missing_recorda_return_404(client, common_user):
    missing_id = uuid.uuid4()
    headers = auth_headers(common_user)

    like_response = client.post(f"{PREFIX}/{missing_id}/likes", headers=headers)
    unlike_response = client.delete(f"{PREFIX}/{missing_id}/likes", headers=headers)

    assert like_response.status_code == 404
    assert unlike_response.status_code == 404


def test_like_and_unlike_require_authentication(client):
    recorda_id = uuid.uuid4()

    assert client.post(f"{PREFIX}/{recorda_id}/likes").status_code == 401
    assert client.delete(f"{PREFIX}/{recorda_id}/likes").status_code == 401
