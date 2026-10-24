"""Account settings with real authentication and database transactions."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Follow, Notification
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING
from app.models.notification import (
    TYPE_FOLLOW_ACCEPTED,
    TYPE_FOLLOW_REQUEST,
    TYPE_NEW_FOLLOWER,
)
from app.services import notification_service
from tests.factories import (
    add_favorite_genres,
    add_follow,
    add_notification,
    add_recorda,
    add_user,
    auth_headers,
)

URL = "/api/v1/users/me/settings"


def pending_request(db, sender, recipient):
    follow = add_follow(db, sender, recipient, status=STATUS_PENDING)
    add_notification(
        db, recipient, TYPE_FOLLOW_REQUEST, sender=sender, follow_id=follow.follow_id
    )
    return follow


@pytest.mark.parametrize("is_private,language", [(False, "pt-BR"), (True, "en")])
def test_get_returns_only_own_settings(client, db, is_private, language):
    user = add_user(db, "owner", is_private=is_private, language=language)
    add_user(db, "other", is_private=not is_private)

    response = client.get(URL, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"is_private": is_private, "language": language}


@pytest.mark.parametrize("method", ["get", "patch"])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_requires_valid_authentication(client, method, headers):
    kwargs = {"json": {"is_private": True}} if method == "patch" else {}
    assert getattr(client, method)(URL, headers=headers, **kwargs).status_code == 401


def test_becoming_private_preserves_accepted_followers(client, db):
    owner = add_user(db, "owner", language="en")
    follower = add_user(db, "follower")
    follow = add_follow(db, follower, owner)
    accepted_at = follow.accepted_at

    response = client.patch(URL, json={"is_private": True}, headers=auth_headers(owner))

    assert response.status_code == 200
    assert response.json() == {
        "is_private": True,
        "language": "en",
        "accepted_requests": 0,
    }
    db.expire_all()
    assert owner.is_private is True
    assert follow.status == STATUS_ACCEPTED
    assert follow.accepted_at == accepted_at
    newcomer = add_user(db, "newcomer")
    assert client.post(
        f"/api/v1/users/{owner.user_id}/follow", headers=auth_headers(newcomer)
    ).json() == {"follow_status": "solicitado"}


def test_becoming_public_accepts_only_incoming_pending_requests(client, db):
    owner = add_user(db, "owner", is_private=True)
    senders = [add_user(db, f"sender{i}") for i in range(2)]
    pending = [pending_request(db, sender, owner) for sender in senders]
    accepted = add_follow(db, add_user(db, "accepted"), owner)
    accepted_at = accepted.accepted_at
    other = add_user(db, "other", is_private=True)
    unrelated = pending_request(db, senders[0], other)
    outgoing = pending_request(db, owner, other)

    response = client.patch(
        URL, json={"is_private": False}, headers=auth_headers(owner)
    )

    assert response.status_code == 200
    assert response.json() == {
        "is_private": False,
        "language": "pt-BR",
        "accepted_requests": 2,
    }
    db.expire_all()
    assert owner.is_private is False
    assert all(f.status == STATUS_ACCEPTED and f.accepted_at for f in pending)
    assert accepted.accepted_at == accepted_at
    assert unrelated.status == outgoing.status == STATUS_PENDING
    for sender, follow in zip(senders, pending, strict=True):
        notifications = list(
            db.scalars(
                select(Notification).where(Notification.follow_id == follow.follow_id)
            )
        )
        assert {(n.recipient_id, n.sender_id, n.type) for n in notifications} == {
            (owner.user_id, sender.user_id, TYPE_NEW_FOLLOWER),
            (sender.user_id, owner.user_id, TYPE_FOLLOW_ACCEPTED),
        }
    again = client.patch(URL, json={"is_private": False}, headers=auth_headers(owner))
    assert again.json()["accepted_requests"] == 0
    assert len(list(db.scalars(select(Notification)))) == 6


@pytest.mark.parametrize("is_private", [False, True])
@pytest.mark.parametrize("payload", [{}, {"is_private": None}])
def test_empty_or_null_update_is_noop(client, db, is_private, payload):
    owner = add_user(db, "owner", is_private=is_private)
    response = client.patch(URL, json=payload, headers=auth_headers(owner))
    assert response.status_code == 200
    assert response.json() == {
        "is_private": is_private,
        "language": "pt-BR",
        "accepted_requests": 0,
    }


def test_invalid_privacy_is_rejected(client, db):
    owner = add_user(db, "owner")
    response = client.patch(
        URL, json={"is_private": "invalid"}, headers=auth_headers(owner)
    )
    assert response.status_code == 422
    db.refresh(owner)
    assert owner.is_private is False


def test_language_and_privacy_can_be_updated_together(client, db):
    owner = add_user(db, "owner")
    response = client.patch(
        URL, json={"is_private": True, "language": "en"}, headers=auth_headers(owner)
    )
    assert response.status_code == 200
    assert response.json()["language"] == "en"


def test_bulk_failure_rolls_back_privacy_follows_and_notifications(
    client, db, monkeypatch
):
    owner = add_user(db, "owner", is_private=True)
    pending = [pending_request(db, add_user(db, f"sender{i}"), owner) for i in range(2)]
    original = notification_service.notify_follow_accepted
    calls = 0

    def fail_after_first_acceptance(db, follow):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("notification failure")
        return original(db, follow)

    monkeypatch.setattr(
        notification_service, "notify_follow_accepted", fail_after_first_acceptance
    )
    with pytest.raises(RuntimeError, match="notification failure"):
        client.patch(
            URL,
            json={"is_private": False, "language": "en"},
            headers=auth_headers(owner),
        )

    # No rollback here: the service must have undone the entire failed operation.
    db.expire_all()
    assert calls == 2
    assert owner.is_private is True
    assert owner.language == "pt-BR"
    assert all(f.status == STATUS_PENDING and f.accepted_at is None for f in pending)
    assert list(db.scalars(select(Notification.type))) == [TYPE_FOLLOW_REQUEST] * 2
    with db.get_bind().connect() as connection:
        assert (
            connection.execute(select(Follow.status)).scalars().all()
            == [STATUS_PENDING] * 2
        )


def test_old_recordas_follow_privacy_immediately_across_all_readers(client, db):
    owner = add_user(db, "owner")
    viewer = add_user(db, "viewer")
    follower = add_user(db, "follower")
    add_follow(db, follower, owner)
    add_follow(db, owner, follower)
    recorda = add_recorda(db, owner)
    for user in (owner, viewer, follower):
        add_favorite_genres(db, user, "Rock")
    owner_headers = auth_headers(owner)
    recorda_id = str(recorda.recorda_id)
    detail = f"/api/v1/recordas/{recorda_id}"
    profile = f"/api/v1/users/{owner.user_id}"

    for private in (False, True, False, True):
        response = client.patch(
            URL, json={"is_private": private}, headers=owner_headers
        )
        assert response.status_code == 200
        for reader in (viewer, follower, owner):
            headers = auth_headers(reader)
            allowed = not private or reader != viewer
            expected = 200 if allowed else 403
            assert client.get(detail, headers=headers).status_code == expected
            for path in ("recordas", "followers", "following"):
                result = client.get(f"{profile}/{path}", headers=headers)
                assert result.status_code == expected
                if path == "recordas" and allowed:
                    assert [r["recorda_id"] for r in result.json()] == [recorda_id]
            feed = client.get("/api/v1/feed/general", headers=headers)
            assert feed.status_code == 200
            assert (
                recorda_id in [r["recorda_id"] for r in feed.json()["items"]]
            ) == allowed
            listing = client.get("/api/v1/recordas", headers=headers)
            assert (recorda_id in [r["recorda_id"] for r in listing.json()]) == allowed


def test_grid_requires_authentication_and_active_owner(client, db):
    owner = add_user(db, "owner")
    viewer = add_user(db, "viewer")
    path = f"/api/v1/users/{owner.user_id}/recordas"
    assert client.get(path).status_code == 401
    for field, value in (("status", "SUSPENDED"), ("deleted_at", owner.created_at)):
        setattr(owner, field, value)
        db.commit()
        assert client.get(path, headers=auth_headers(viewer)).status_code == 404
        owner.status = "ACTIVE"
    assert (
        client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000/recordas",
            headers=auth_headers(viewer),
        ).status_code
        == 404
    )


def test_grid_excludes_deleted_recordas_and_orders_newest_first(client, db):
    owner = add_user(db, "owner")
    older = add_recorda(db, owner, created_at=datetime(2025, 1, 1, tzinfo=UTC))
    newer = add_recorda(db, owner, created_at=datetime(2025, 1, 2, tzinfo=UTC))
    add_recorda(db, owner, deleted_at=owner.created_at)
    response = client.get(
        f"/api/v1/users/{owner.user_id}/recordas", headers=auth_headers(owner)
    )
    assert response.status_code == 200
    assert [r["recorda_id"] for r in response.json()] == [
        str(newer.recorda_id),
        str(older.recorda_id),
    ]


@pytest.mark.parametrize(
    "field,value", [("status", "SUSPENDED"), ("deleted_at", "deleted")]
)
def test_inactive_account_cannot_read_or_change_settings(client, db, field, value):
    owner = add_user(db, "owner")
    headers = auth_headers(owner)
    setattr(owner, field, owner.created_at if field == "deleted_at" else value)
    db.commit()
    assert client.get(URL, headers=headers).status_code == 401
    assert (
        client.patch(URL, headers=headers, json={"is_private": True}).status_code == 401
    )


def test_same_value_leaves_pending_requests_untouched(client, db):
    owner = add_user(db, "owner", is_private=True)
    follow = pending_request(db, add_user(db, "sender"), owner)
    response = client.patch(URL, headers=auth_headers(owner), json={"is_private": True})
    assert response.status_code == 200
    assert response.json()["accepted_requests"] == 0
    db.refresh(follow)
    assert follow.status == STATUS_PENDING
    assert list(db.scalars(select(Notification.type))) == [TYPE_FOLLOW_REQUEST]


def test_individual_acceptance_rolls_back_when_notification_fails(
    client, db, monkeypatch
):
    owner = add_user(db, "owner", is_private=True)
    follow = pending_request(db, add_user(db, "sender"), owner)

    def fail_notification(db, follow):
        raise RuntimeError("notification failure")

    monkeypatch.setattr(
        notification_service, "notify_follow_accepted", fail_notification
    )
    with pytest.raises(RuntimeError, match="notification failure"):
        client.patch(
            f"/api/v1/follow-requests/{follow.follow_id}",
            headers=auth_headers(owner),
            json={"action": "accept"},
        )
    db.expire_all()
    assert follow.status == STATUS_PENDING
    assert follow.accepted_at is None
    assert list(db.scalars(select(Notification.type))) == [TYPE_FOLLOW_REQUEST]


@pytest.mark.parametrize("initial_private", [True, False])
def test_new_follow_uses_latest_privacy_even_when_target_is_cached(
    client, db, initial_private
):
    owner = add_user(db, "owner", is_private=initial_private)
    sender = add_user(db, "sender")
    assert owner.is_private == initial_private
    # Another request changes the account after this session loaded the owner.
    with Session(db.get_bind()) as concurrent:
        target = concurrent.get(type(owner), owner.user_id)
        target.is_private = not initial_private
        concurrent.commit()

    response = client.post(
        f"/api/v1/users/{owner.user_id}/follow", headers=auth_headers(sender)
    )

    assert response.status_code == 200
    assert response.json()["follow_status"] == (
        "seguindo" if initial_private else "solicitado"
    )
