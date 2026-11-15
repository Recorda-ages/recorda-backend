import uuid
from datetime import UTC, datetime

from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from tests.factories import add_follow, add_like, add_recorda, add_user, auth_headers

STAMP = datetime(2026, 11, 15, 15, tzinfo=UTC)


def month_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/calendar"


def day_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/calendar/day"


def test_requires_authentication(client, db):
    owner = add_user(db, "owner")

    response = client.get(month_url(owner), params={"year": 2026, "month": 11})

    assert response.status_code == 401


def test_public_account_month_is_visible_to_any_user(client, db):
    owner = add_user(db, "owner")
    viewer = add_user(db, "viewer")
    recorda = add_recorda(db, owner, created_at=STAMP)
    add_recorda(db, viewer, created_at=STAMP)

    response = client.get(
        month_url(owner),
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_memories"] == 1
    assert body["days"][0]["first_recorda_id"] == str(recorda.recorda_id)


def test_private_account_month_is_forbidden_to_non_followers(client, db):
    owner = add_user(db, "owner", is_private=True)
    viewer = add_user(db, "viewer")
    add_recorda(db, owner, created_at=STAMP)

    response = client.get(
        month_url(owner),
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403


def test_private_account_month_is_forbidden_to_pending_followers(client, db):
    owner = add_user(db, "owner", is_private=True)
    viewer = add_user(db, "viewer")
    add_follow(db, viewer, owner, status=STATUS_PENDING)

    response = client.get(
        month_url(owner),
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 403


def test_private_account_month_is_visible_to_accepted_followers(client, db):
    owner = add_user(db, "owner", is_private=True)
    viewer = add_user(db, "viewer")
    add_follow(db, viewer, owner)
    add_recorda(db, owner, created_at=STAMP)

    response = client.get(
        month_url(owner),
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )

    assert response.status_code == 200
    assert response.json()["active_days_count"] == 1


def test_unknown_and_suspended_users_are_not_found(client, db):
    viewer = add_user(db, "viewer")
    suspended = add_user(db, "gone", status=STATUS_SUSPENDED)

    unknown = client.get(
        f"/api/v1/users/{uuid.uuid4()}/calendar",
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )
    gone = client.get(
        month_url(suspended),
        params={"year": 2026, "month": 11},
        headers=auth_headers(viewer),
    )

    assert unknown.status_code == 404
    assert gone.status_code == 404


def test_day_uses_owner_memories_and_viewer_like_state(client, db):
    owner = add_user(db, "owner")
    viewer = add_user(db, "viewer")
    recorda = add_recorda(db, owner, created_at=STAMP)
    add_like(db, viewer, recorda)

    response = client.get(
        day_url(owner), params={"date": "2026-11-15"}, headers=auth_headers(viewer)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    memory = body["memories"][0]
    assert memory["author"]["user_id"] == str(owner.user_id)
    assert memory["likes_count"] == 1
    assert memory["is_liked"] is True


def test_day_of_private_account_is_forbidden_to_non_followers(client, db):
    owner = add_user(db, "owner", is_private=True)
    viewer = add_user(db, "viewer")
    add_recorda(db, owner, created_at=STAMP)

    response = client.get(
        day_url(owner), params={"date": "2026-11-15"}, headers=auth_headers(viewer)
    )

    assert response.status_code == 403


def test_own_id_returns_own_calendar(client, db):
    owner = add_user(db, "owner", is_private=True)
    add_recorda(db, owner, created_at=STAMP)

    response = client.get(
        month_url(owner),
        params={"year": 2026, "month": 11},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["total_memories"] == 1
