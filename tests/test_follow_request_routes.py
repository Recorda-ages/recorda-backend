"""Endpoint tests for /api/v1/follow-requests."""

from sqlalchemy import select

from app.models import Follow, Notification
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING
from app.models.notification import (
    TYPE_FOLLOW_ACCEPTED,
    TYPE_FOLLOW_REQUEST,
    TYPE_NEW_FOLLOWER,
)
from tests.factories import add_follow, add_notification, add_user, auth_headers


def request_url(follow) -> str:
    return f"/api/v1/follow-requests/{follow.follow_id}"


def pending_request(db, follower, following):
    follow = add_follow(db, follower, following, status=STATUS_PENDING)
    add_notification(
        db,
        following,
        TYPE_FOLLOW_REQUEST,
        sender=follower,
        follow_id=follow.follow_id,
    )
    return follow


def find_follow(db, follow_id) -> Follow | None:
    db.expire_all()
    return db.get(Follow, follow_id)


def notifications_of(db, user) -> list[str]:
    stmt = select(Notification.type).where(Notification.recipient_id == user.user_id)
    return list(db.scalars(stmt))


class TestAccept:
    def test_turns_the_request_into_an_active_follow(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.patch(
            request_url(follow), json={"action": "accept"}, headers=auth_headers(alice)
        )

        assert response.status_code == 204
        accepted = find_follow(db, follow.follow_id)
        assert accepted.status == STATUS_ACCEPTED
        assert accepted.accepted_at is not None

    def test_notifies_the_sender(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        client.patch(
            request_url(follow), json={"action": "accept"}, headers=auth_headers(alice)
        )

        assert notifications_of(db, bob) == [TYPE_FOLLOW_ACCEPTED]

    def test_request_notification_becomes_new_follower(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        client.patch(
            request_url(follow), json={"action": "accept"}, headers=auth_headers(alice)
        )

        assert notifications_of(db, alice) == [TYPE_NEW_FOLLOWER]

    def test_only_the_recipient_can_accept(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        for user in (bob, add_user(db, "carol")):
            response = client.patch(
                request_url(follow),
                json={"action": "accept"},
                headers=auth_headers(user),
            )
            assert response.status_code == 403

        assert find_follow(db, follow.follow_id).status == STATUS_PENDING

    def test_cannot_accept_twice(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)
        headers = auth_headers(alice)
        client.patch(request_url(follow), json={"action": "accept"}, headers=headers)

        response = client.patch(
            request_url(follow), json={"action": "accept"}, headers=headers
        )

        assert response.status_code == 409
        assert notifications_of(db, bob) == [TYPE_FOLLOW_ACCEPTED]


class TestDecline:
    def test_removes_the_request(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.patch(
            request_url(follow), json={"action": "decline"}, headers=auth_headers(alice)
        )

        assert response.status_code == 204
        assert find_follow(db, follow.follow_id) is None

    def test_does_not_notify_anyone(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        client.patch(
            request_url(follow), json={"action": "decline"}, headers=auth_headers(alice)
        )

        assert notifications_of(db, bob) == []
        assert notifications_of(db, alice) == []

    def test_only_the_recipient_can_decline(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.patch(
            request_url(follow), json={"action": "decline"}, headers=auth_headers(bob)
        )

        assert response.status_code == 403
        assert find_follow(db, follow.follow_id) is not None

    def test_cannot_decline_an_accepted_follow(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = add_follow(db, bob, alice)

        response = client.patch(
            request_url(follow), json={"action": "decline"}, headers=auth_headers(alice)
        )

        assert response.status_code == 409
        assert find_follow(db, follow.follow_id).status == STATUS_ACCEPTED

    def test_cannot_decline_twice(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)
        headers = auth_headers(alice)
        client.patch(request_url(follow), json={"action": "decline"}, headers=headers)

        response = client.patch(
            request_url(follow), json={"action": "decline"}, headers=headers
        )

        assert response.status_code == 404


class TestCancel:
    def test_sender_cancels_the_request(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.delete(request_url(follow), headers=auth_headers(bob))

        assert response.status_code == 204
        assert find_follow(db, follow.follow_id) is None
        assert notifications_of(db, alice) == []

    def test_only_the_sender_can_cancel(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.delete(request_url(follow), headers=auth_headers(alice))

        assert response.status_code == 403
        assert find_follow(db, follow.follow_id) is not None

    def test_cannot_cancel_an_accepted_follow(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = add_follow(db, bob, alice)

        response = client.delete(request_url(follow), headers=auth_headers(bob))

        assert response.status_code == 409

    def test_cannot_cancel_twice(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)
        client.delete(request_url(follow), headers=auth_headers(bob))

        response = client.delete(request_url(follow), headers=auth_headers(bob))

        assert response.status_code == 404


class TestValidation:
    def test_unknown_request_is_404(self, client, db):
        alice = add_user(db, "alice")
        url = "/api/v1/follow-requests/00000000-0000-0000-0000-000000000000"

        response = client.patch(
            url, json={"action": "accept"}, headers=auth_headers(alice)
        )

        assert response.status_code == 404

    def test_rejects_an_unknown_action(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        response = client.patch(
            request_url(follow), json={"action": "ignore"}, headers=auth_headers(alice)
        )

        assert response.status_code == 422

    def test_requires_authentication(self, client, db):
        alice, bob = add_user(db, "alice"), add_user(db, "bob")
        follow = pending_request(db, bob, alice)

        assert (
            client.patch(request_url(follow), json={"action": "accept"}).status_code
            == 401
        )
        assert client.delete(request_url(follow)).status_code == 401
