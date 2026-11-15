"""Contas suspensas somem das leituras do app comum e voltam ao reativar (issue #90).

Cada teste muda o status direto no banco, sem depender da API de suspensão.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser
from app.models.app_user import STATUS_ACTIVE, STATUS_SUSPENDED
from app.models.notification import (
    TYPE_COMMENT,
    TYPE_CONTENT_REMOVED,
    TYPE_NEW_FOLLOWER,
)
from app.repositories import general_feed_repository, media_storage_repository
from tests.factories import (
    add_comment,
    add_favorite_genres,
    add_follow,
    add_notification,
    add_recorda,
    add_user,
    auth_headers,
)

API = "/api/v1"
MEDIA_PREFIX = f"{API}/recordas/media"
JPEG = b"\xff\xd8\xff" + b"\x00" * 100


def _set_status(db: Session, user: AppUser, status: str) -> None:
    user.status = status
    db.commit()


@pytest.fixture
def viewer(db: Session) -> AppUser:
    return add_user(db, "viewer")


@pytest.fixture
def target(db: Session) -> AppUser:
    return add_user(db, "alvo")


def _usernames(rows) -> list[str]:
    return [row["username"] for row in rows]


def test_search_hides_suspended_user_until_reactivated(client, db, viewer, target):
    def search():
        resp = client.get(
            f"{API}/users/search", params={"q": "alvo"}, headers=auth_headers(viewer)
        )
        return _usernames(resp.json())

    assert search() == ["alvo"]
    _set_status(db, target, STATUS_SUSPENDED)
    assert search() == []
    _set_status(db, target, STATUS_ACTIVE)
    assert search() == ["alvo"]


def test_suggestions_hide_suspended_user_until_reactivated(client, db, viewer, target):
    add_favorite_genres(db, viewer, "Rock")
    add_favorite_genres(db, target, "Rock")

    def suggestions():
        resp = client.get(f"{API}/users/suggestions", headers=auth_headers(viewer))
        return _usernames(resp.json())

    assert suggestions() == ["alvo"]
    _set_status(db, target, STATUS_SUSPENDED)
    assert suggestions() == []
    _set_status(db, target, STATUS_ACTIVE)
    assert suggestions() == ["alvo"]


def _recorda_ids(client: TestClient, viewer: AppUser) -> set[str]:
    resp = client.get(f"{API}/recordas", headers=auth_headers(viewer))
    assert resp.status_code == 200
    return {item["recorda_id"] for item in resp.json()}


def test_list_recordas_hides_suspended_author_until_reactivated(
    client, db, viewer, target
):
    recorda_id = str(add_recorda(db, target).recorda_id)

    assert _recorda_ids(client, viewer) == {recorda_id}
    _set_status(db, target, STATUS_SUSPENDED)
    assert _recorda_ids(client, viewer) == set()
    _set_status(db, target, STATUS_ACTIVE)
    assert _recorda_ids(client, viewer) == {recorda_id}


def test_list_recordas_keeps_privacy_rules(client, db, viewer):
    private_author = add_user(db, "privado", is_private=True)
    hidden = str(add_recorda(db, private_author).recorda_id)
    own = str(add_recorda(db, add_user(db, "eu", is_private=True)).recorda_id)
    owner = db.query(AppUser).filter_by(username="eu").one()

    assert hidden not in _recorda_ids(client, viewer)
    assert _recorda_ids(client, owner) >= {own}

    add_follow(db, viewer, private_author)
    assert hidden in _recorda_ids(client, viewer)


def test_general_feed_final_query_requires_active_author(db, viewer, target):
    recorda = add_recorda(db, target)

    def feed_ids():
        query = general_feed_repository.get_general_feed_query(
            viewer.user_id, [target.user_id]
        )
        return [row[0].recorda_id for row in db.execute(query).all()]

    assert feed_ids() == [recorda.recorda_id]
    _set_status(db, target, STATUS_SUSPENDED)
    assert feed_ids() == []
    _set_status(db, target, STATUS_ACTIVE)
    assert feed_ids() == [recorda.recorda_id]


def test_comments_hide_suspended_commenter_on_active_recorda(
    client, db, viewer, target
):
    recorda = add_recorda(db, viewer)
    add_comment(db, target, recorda)
    url = f"{API}/recordas/{recorda.recorda_id}/comments"

    def commenters():
        resp = client.get(url, headers=auth_headers(viewer))
        assert resp.status_code == 200
        return _usernames(resp.json())

    assert commenters() == ["alvo"]
    _set_status(db, target, STATUS_SUSPENDED)
    assert commenters() == []
    _set_status(db, target, STATUS_ACTIVE)
    assert commenters() == ["alvo"]


def _notifications(client: TestClient, viewer: AppUser) -> tuple[list[str], int]:
    body = client.get(f"{API}/notifications", headers=auth_headers(viewer)).json()
    return [item["type"] for item in body["items"]], body["unread_count"]


def test_notifications_hide_suspended_sender_until_reactivated(
    client, db, viewer, target
):
    add_notification(db, viewer, TYPE_NEW_FOLLOWER, sender=target)

    assert _notifications(client, viewer) == ([TYPE_NEW_FOLLOWER], 1)
    _set_status(db, target, STATUS_SUSPENDED)
    assert _notifications(client, viewer) == ([], 0)
    _set_status(db, target, STATUS_ACTIVE)
    assert _notifications(client, viewer) == ([TYPE_NEW_FOLLOWER], 1)


def test_notifications_hide_recorda_of_suspended_author(client, db, viewer, target):
    sender = add_user(db, "remetente")
    recorda = add_recorda(db, target)
    add_notification(
        db, viewer, TYPE_COMMENT, sender=sender, recorda_id=recorda.recorda_id
    )

    assert _notifications(client, viewer) == ([TYPE_COMMENT], 1)
    _set_status(db, target, STATUS_SUSPENDED)
    assert _notifications(client, viewer) == ([], 0)
    _set_status(db, target, STATUS_ACTIVE)
    assert _notifications(client, viewer) == ([TYPE_COMMENT], 1)


def test_notifications_keep_system_notifications_without_sender(client, db, viewer):
    recorda = add_recorda(db, viewer, deleted_at=now_utc())
    add_notification(db, viewer, TYPE_CONTENT_REMOVED, recorda_id=recorda.recorda_id)

    assert _notifications(client, viewer) == ([TYPE_CONTENT_REMOVED], 1)


def test_content_removed_notification_hides_suspended_author(
    client, db, viewer, target
):
    recorda = add_recorda(db, target, deleted_at=now_utc())
    add_notification(db, viewer, TYPE_CONTENT_REMOVED, recorda_id=recorda.recorda_id)

    _set_status(db, target, STATUS_SUSPENDED)
    assert _notifications(client, viewer) == ([], 0)
    _set_status(db, target, STATUS_ACTIVE)
    assert _notifications(client, viewer) == ([TYPE_CONTENT_REMOVED], 1)


def test_media_shared_by_hidden_and_visible_recordas_stays_available(
    client, db, viewer, target
):
    url = _publish_media(db, target)
    add_recorda(db, add_user(db, "outro"), media_url=url)

    _set_status(db, target, STATUS_SUSPENDED)
    assert client.get(url, headers=auth_headers(viewer)).status_code == 200


def _publish_media(db: Session, author: AppUser, filename: str = "pub.jpg") -> str:
    media_storage_repository.save(db, filename, JPEG, "image/jpeg")
    add_recorda(db, author, media_url=f"{MEDIA_PREFIX}/{filename}")
    return f"{MEDIA_PREFIX}/{filename}"


def test_media_of_suspended_author_returns_404_until_reactivated(
    client, db, viewer, target
):
    url = _publish_media(db, target)
    headers = auth_headers(viewer)

    assert client.get(url, headers=headers).status_code == 200
    _set_status(db, target, STATUS_SUSPENDED)
    assert client.get(url, headers=headers).status_code == 404
    assert client.get(url, headers={**headers, "Range": "bytes=0-1"}).status_code == 404
    assert (
        client.get(url, headers={**headers, "Range": "bytes=9999-"}).status_code == 404
    )
    _set_status(db, target, STATUS_ACTIVE)
    assert client.get(url, headers=headers).status_code == 200


def test_media_keeps_authorized_range_requests(client, db, viewer, target):
    url = _publish_media(db, target)

    resp = client.get(url, headers={**auth_headers(viewer), "Range": "bytes=0-1"})

    assert resp.status_code == 206
    assert resp.content == JPEG[:2]


def test_media_of_private_author_requires_accepted_follow(client, db, viewer):
    private_author = add_user(db, "privado", is_private=True)
    url = _publish_media(db, private_author)

    assert client.get(url, headers=auth_headers(viewer)).status_code == 404
    assert client.get(url, headers=auth_headers(private_author)).status_code == 200
    add_follow(db, viewer, private_author)
    assert client.get(url, headers=auth_headers(viewer)).status_code == 200


def test_media_of_deleted_recorda_returns_404(client, db, viewer, target):
    media_storage_repository.save(db, "gone.jpg", JPEG, "image/jpeg")
    add_recorda(db, target, media_url=f"{MEDIA_PREFIX}/gone.jpg", deleted_at=now_utc())

    resp = client.get(f"{MEDIA_PREFIX}/gone.jpg", headers=auth_headers(viewer))

    assert resp.status_code == 404


def test_admin_reads_media_of_suspended_author(client, db, admin_user, target):
    url = _publish_media(db, target)
    _set_status(db, target, STATUS_SUSPENDED)

    assert client.get(url, headers=auth_headers(admin_user)).status_code == 200


def test_unpublished_media_preview_stays_available(client, db, viewer):
    media_storage_repository.save(db, "draft.jpg", JPEG, "image/jpeg")

    resp = client.get(f"{MEDIA_PREFIX}/draft.jpg", headers=auth_headers(viewer))

    assert resp.status_code == 200
    assert resp.content == JPEG


def test_already_protected_reads_follow_suspension(client, db, viewer, target):
    """Feed Seguindo, detalhe e seguidores já filtravam; aqui só a regressão."""
    recorda = add_recorda(db, target)
    add_follow(db, target, viewer)
    add_follow(db, viewer, target)
    headers = auth_headers(viewer)

    def snapshot():
        feed = client.get(f"{API}/feed/following", headers=headers).json()["items"]
        detail = client.get(f"{API}/recordas/{recorda.recorda_id}", headers=headers)
        followers = client.get(
            f"{API}/users/{viewer.user_id}/followers", headers=headers
        ).json()
        return len(feed), detail.status_code, _usernames(followers)

    assert snapshot() == (1, 200, ["alvo"])
    _set_status(db, target, STATUS_SUSPENDED)
    assert snapshot() == (0, 404, [])
    _set_status(db, target, STATUS_ACTIVE)
    assert snapshot() == (1, 200, ["alvo"])
