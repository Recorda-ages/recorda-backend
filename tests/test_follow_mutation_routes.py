from sqlalchemy import select

from app.models import Follow, Notification
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING
from tests.factories import add_user, auth_headers


def follow_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/follow"


def test_public_follow_creates_accepted_relationship_and_notification(
    client, db, common_user
):
    target = add_user(db, "public_target")

    response = client.post(follow_url(target), headers=auth_headers(common_user))

    assert response.status_code == 200
    assert response.json() == {"follow_status": "seguindo"}
    follow = db.scalars(
        select(Follow).where(
            Follow.follower_id == common_user.user_id,
            Follow.following_id == target.user_id,
        )
    ).one()
    assert follow.status == STATUS_ACCEPTED
    assert follow.accepted_at is not None
    notification = db.scalars(
        select(Notification).where(Notification.follow_id == follow.follow_id)
    ).one()
    assert notification.type == "NEW_FOLLOWER"
    assert notification.recipient_id == target.user_id


def test_private_follow_creates_pending_request_and_notification(
    client, db, common_user
):
    target = add_user(db, "private_target", is_private=True)

    response = client.post(follow_url(target), headers=auth_headers(common_user))

    assert response.status_code == 200
    assert response.json() == {"follow_status": "solicitado"}
    follow = db.scalars(
        select(Follow).where(
            Follow.follower_id == common_user.user_id,
            Follow.following_id == target.user_id,
        )
    ).one()
    assert follow.status == STATUS_PENDING
    assert follow.accepted_at is None
    notification = db.scalars(
        select(Notification).where(Notification.follow_id == follow.follow_id)
    ).one()
    assert notification.type == "FOLLOW_REQUEST"
    assert notification.recipient_id == target.user_id


def test_duplicate_follow_is_conflict_and_does_not_duplicate_notification(
    client, db, common_user
):
    target = add_user(db, "duplicate_target")
    headers = auth_headers(common_user)

    first = client.post(follow_url(target), headers=headers)
    second = client.post(follow_url(target), headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    notifications = db.scalars(
        select(Notification).where(Notification.recipient_id == target.user_id)
    ).all()
    assert len(notifications) == 1


def test_follow_rejects_self_and_unknown_user(client, common_user):
    headers = auth_headers(common_user)

    self_follow = client.post(follow_url(common_user), headers=headers)
    unknown_user = client.post(
        "/api/v1/users/00000000-0000-0000-0000-000000000000/follow",
        headers=headers,
    )

    assert self_follow.status_code == 400
    assert unknown_user.status_code == 404


def test_follow_and_unfollow_require_authentication(client, common_user):
    assert client.post(follow_url(common_user)).status_code == 401
    assert client.delete(follow_url(common_user)).status_code == 401


def test_unfollow_only_removes_the_authenticated_users_relationship(
    client, db, common_user
):
    target = add_user(db, "unfollow_target")
    intruder = add_user(db, "unfollow_intruder")
    headers = auth_headers(common_user)
    intruder_headers = auth_headers(intruder)
    client.post(follow_url(target), headers=headers)

    forbidden = client.delete(follow_url(target), headers=intruder_headers)
    removed = client.delete(follow_url(target), headers=headers)

    assert forbidden.status_code == 404
    assert removed.status_code == 200
    assert removed.json() == {"follow_status": "nenhuma"}
    assert (
        db.scalars(
            select(Follow).where(
                Follow.follower_id == common_user.user_id,
                Follow.following_id == target.user_id,
            )
        ).first()
        is None
    )
