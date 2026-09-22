from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.app_user import AppUser
from app.models.follow import STATUS_ACCEPTED
from tests.factories import (
    add_follow,
    add_notification,
    add_recorda,
    add_user,
    auth_headers,
    token_for,
)

LIST_URL = "/api/v1/notifications"
READ_ALL_URL = "/api/v1/notifications/read-all"

NOW = datetime.now(UTC)


@pytest.fixture
def sender(db: Session) -> AppUser:
    return add_user(db, "lucas_almeida", name="Lucas Almeida")


def test_requires_authentication(client: TestClient):
    assert client.get(LIST_URL).status_code == 401
    assert client.post(READ_ALL_URL).status_code == 401


def test_rejects_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer not-a-valid-token"}

    assert client.get(LIST_URL, headers=headers).status_code == 401
    assert client.post(READ_ALL_URL, headers=headers).status_code == 401


def test_rejects_expired_token(client: TestClient, common_user: AppUser):
    token = token_for(common_user, expires_delta=timedelta(minutes=-1))
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(LIST_URL, headers=headers).status_code == 401
    assert client.post(READ_ALL_URL, headers=headers).status_code == 401


def test_routes_carry_the_padlock_in_the_docs(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    assert paths["/api/v1/notifications"]["get"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/notifications/read-all"]["post"]["security"] == [
        {"HTTPBearer": []}
    ]


def test_lists_from_newest_to_oldest(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    add_notification(
        db, common_user, "LIKE", sender=sender, created_at=NOW - timedelta(hours=2)
    )
    add_notification(
        db,
        common_user,
        "NEW_FOLLOWER",
        sender=sender,
        created_at=NOW - timedelta(minutes=1),
    )
    add_notification(db, common_user, "MENTION", created_at=NOW - timedelta(days=1))

    response = client.get(LIST_URL, headers=auth_headers(common_user))

    assert response.status_code == 200
    assert [item["type"] for item in response.json()["items"]] == [
        "NEW_FOLLOWER",
        "LIKE",
        "MENTION",
    ]


def test_only_returns_notifications_of_the_authenticated_user(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    mine = add_notification(db, common_user, "LIKE", sender=sender)
    add_notification(db, sender, "LIKE", sender=common_user)

    response = client.get(LIST_URL, headers=auth_headers(common_user))
    items = response.json()["items"]

    assert [item["notification_id"] for item in items] == [str(mine.notification_id)]


def test_follow_request_carries_data_to_accept_or_decline(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    follow = add_follow(db, sender, common_user)
    add_notification(
        db, common_user, "FOLLOW_REQUEST", sender=sender, follow_id=follow.follow_id
    )

    item = client.get(LIST_URL, headers=auth_headers(common_user)).json()["items"][0]

    assert item["follow_id"] == str(follow.follow_id)
    assert item["sender"] == {
        "user_id": str(sender.user_id),
        "username": "lucas_almeida",
        "profile_picture_url": None,
    }


def test_system_notification_has_no_sender(
    client: TestClient, db: Session, common_user: AppUser
):
    add_notification(db, common_user, "MENTION")

    item = client.get(LIST_URL, headers=auth_headers(common_user)).json()["items"][0]

    assert item["sender"] is None


def test_hides_notifications_from_deleted_senders(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    add_notification(db, common_user, "NEW_FOLLOWER", sender=sender)
    sender.deleted_at = NOW
    db.commit()

    body = client.get(LIST_URL, headers=auth_headers(common_user)).json()

    assert body["items"] == []
    assert body["unread_count"] == 0


def test_hides_notifications_of_deleted_recordas(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    recorda = add_recorda(db, common_user)
    add_notification(
        db, common_user, "LIKE", sender=sender, recorda_id=recorda.recorda_id
    )
    recorda.deleted_at = NOW
    db.commit()

    body = client.get(LIST_URL, headers=auth_headers(common_user)).json()

    assert body["items"] == []
    assert body["unread_count"] == 0


def test_unread_count_ignores_read_notifications(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    add_notification(db, common_user, "LIKE", sender=sender)
    add_notification(db, common_user, "NEW_FOLLOWER", sender=sender, is_read=True)

    body = client.get(LIST_URL, headers=auth_headers(common_user)).json()

    assert len(body["items"]) == 2
    assert body["unread_count"] == 1


def test_read_all_zeroes_the_unread_count(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    add_notification(db, common_user, "LIKE", sender=sender)
    add_notification(db, common_user, "NEW_FOLLOWER", sender=sender)
    headers = auth_headers(common_user)

    assert client.get(LIST_URL, headers=headers).json()["unread_count"] == 2

    response = client.post(READ_ALL_URL, headers=headers)

    assert response.status_code == 204
    body = client.get(LIST_URL, headers=headers).json()
    assert body["unread_count"] == 0
    assert all(item["is_read"] for item in body["items"])


def test_read_all_does_not_touch_other_users(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    add_notification(db, sender, "LIKE", sender=common_user)

    client.post(READ_ALL_URL, headers=auth_headers(common_user))

    assert (
        client.get(LIST_URL, headers=auth_headers(sender)).json()["unread_count"] == 1
    )


def test_pagination_walks_the_list(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    for minutes in range(3):
        add_notification(
            db,
            common_user,
            "LIKE",
            sender=sender,
            created_at=NOW - timedelta(minutes=minutes),
        )

    headers = auth_headers(common_user)
    first = client.get(LIST_URL, params={"limit": 2}, headers=headers).json()
    second = client.get(
        LIST_URL, params={"limit": 2, "offset": 2}, headers=headers
    ).json()

    assert len(first["items"]) == 2
    assert len(second["items"]) == 1
    assert second["items"][0]["notification_id"] not in [
        item["notification_id"] for item in first["items"]
    ]


def test_rejects_invalid_pagination(client: TestClient, common_user: AppUser):
    headers = auth_headers(common_user)

    assert client.get(LIST_URL, params={"limit": 0}, headers=headers).status_code == 422
    assert (
        client.get(LIST_URL, params={"limit": 51}, headers=headers).status_code == 422
    )
    assert (
        client.get(LIST_URL, params={"offset": -1}, headers=headers).status_code == 422
    )


def test_accepted_follow_is_listed_for_the_requester(
    client: TestClient, db: Session, common_user: AppUser, sender: AppUser
):
    follow = add_follow(db, common_user, sender, status=STATUS_ACCEPTED)
    add_notification(
        db,
        common_user,
        "FOLLOW_ACCEPTED",
        sender=sender,
        follow_id=follow.follow_id,
    )

    item = client.get(LIST_URL, headers=auth_headers(common_user)).json()["items"][0]

    assert item["type"] == "FOLLOW_ACCEPTED"
    assert item["follow_id"] == str(follow.follow_id)
