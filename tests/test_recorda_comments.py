"""Comments on a Recorda respect visibility and notify its author."""

from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.time import now_utc
from app.models import Notification, RecordaComment
from app.models.follow import STATUS_PENDING
from app.models.notification import TYPE_COMMENT
from tests.factories import (
    add_comment,
    add_follow,
    add_recorda,
    add_user,
    auth_headers,
)


def comments_url(recorda) -> str:
    return f"/api/v1/recordas/{recorda.recorda_id}/comments"


def test_comments_are_flat_chronological_and_exclude_deleted(client, db):
    owner = add_user(db, "owner")
    visitor = add_user(db, "visitor", profile_picture_url="/avatars/visitor.jpg")
    recorda = add_recorda(db, owner)
    later = add_comment(db, visitor, recorda, created_at=now_utc())
    earlier = add_comment(
        db, owner, recorda, content="Primeiro", created_at=now_utc() - timedelta(days=1)
    )
    deleted = add_comment(db, owner, recorda, deleted_at=now_utc())

    response = client.get(comments_url(recorda), headers=auth_headers(visitor))

    assert response.status_code == 200
    assert [item["comment_id"] for item in response.json()] == [
        str(earlier.comment_id),
        str(later.comment_id),
    ]
    assert response.json()[1] == {
        "comment_id": str(later.comment_id),
        "user_id": str(visitor.user_id),
        "username": visitor.username,
        "avatar_url": "/avatars/visitor.jpg",
        "content": later.content,
        "created_at": later.created_at.isoformat(),
    }
    assert all(
        item["comment_id"] != str(deleted.comment_id) for item in response.json()
    )


def test_create_comment_persists_and_notifies_owner(client, db):
    owner = add_user(db, "owner")
    visitor = add_user(db, "visitor")
    recorda = add_recorda(db, owner)

    response = client.post(
        comments_url(recorda),
        json={"content": "  Que lembrança boa!  "},
        headers=auth_headers(visitor),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Que lembrança boa!"
    assert body["username"] == visitor.username
    comment = db.get(RecordaComment, UUID(body["comment_id"]))
    assert comment is not None
    notifications = db.scalars(select(Notification)).all()
    assert len(notifications) == 1
    assert notifications[0].type == TYPE_COMMENT
    assert notifications[0].recipient_id == owner.user_id
    assert notifications[0].sender_id == visitor.user_id
    assert notifications[0].recorda_id == recorda.recorda_id
    assert notifications[0].comment_id == comment.comment_id


def test_owner_comment_does_not_notify_self(client, db):
    owner = add_user(db, "owner")
    recorda = add_recorda(db, owner)

    response = client.post(
        comments_url(recorda),
        json={"content": "Minha memória"},
        headers=auth_headers(owner),
    )

    assert response.status_code == 201
    assert db.scalars(select(Notification)).all() == []


def test_comment_length_and_blank_content_are_rejected(client, db):
    owner = add_user(db, "owner")
    recorda = add_recorda(db, owner)
    url = comments_url(recorda)

    assert (
        client.post(
            url, json={"content": "x" * 500}, headers=auth_headers(owner)
        ).status_code
        == 201
    )
    for content in ("x" * 501, "   ", ""):
        response = client.post(
            url, json={"content": content}, headers=auth_headers(owner)
        )
        assert response.status_code == 422

    assert len(db.scalars(select(RecordaComment)).all()) == 1


def test_private_recorda_requires_accepted_follow_for_list_and_create(client, db):
    owner = add_user(db, "owner", is_private=True)
    visitor = add_user(db, "visitor")
    recorda = add_recorda(db, owner)
    url = comments_url(recorda)

    for method in ("get", "post"):
        kwargs = {"json": {"content": "Olá"}} if method == "post" else {}
        response = getattr(client, method)(url, headers=auth_headers(visitor), **kwargs)
        assert response.status_code == 403

    follow = add_follow(db, visitor, owner, status=STATUS_PENDING)
    assert client.get(url, headers=auth_headers(visitor)).status_code == 403
    follow.status = "ACCEPTED"
    db.commit()
    assert client.get(url, headers=auth_headers(visitor)).status_code == 200
    assert (
        client.post(
            url, json={"content": "Olá"}, headers=auth_headers(visitor)
        ).status_code
        == 201
    )


def test_missing_deleted_and_unauthenticated_recordas(client, db):
    owner = add_user(db, "owner")
    recorda = add_recorda(db, owner)
    missing = f"/api/v1/recordas/{uuid4()}/comments"

    assert client.get(comments_url(recorda)).status_code == 401
    assert (
        client.post(comments_url(recorda), json={"content": "Olá"}).status_code == 401
    )
    assert client.get(missing, headers=auth_headers(owner)).status_code == 404
    assert (
        client.post(
            missing, json={"content": "Olá"}, headers=auth_headers(owner)
        ).status_code
        == 404
    )

    recorda.deleted_at = now_utc()
    db.commit()
    assert (
        client.get(comments_url(recorda), headers=auth_headers(owner)).status_code
        == 404
    )
