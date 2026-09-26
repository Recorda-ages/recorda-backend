"""Endpoint tests for the Recorda API under /api/v1/recordas."""

import uuid

import pytest

from tests.factories import add_follow, add_recorda, add_user, auth_headers

PREFIX = "/api/v1/recordas"
MISSING_ID = uuid.uuid4()


@pytest.fixture
def auth(common_user_token):
    return {"Authorization": f"Bearer {common_user_token}"}


def test_list_recordas_empty(client, auth):
    resp = client.get(PREFIX, headers=auth)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_recordas_returns_live_recordas_newest_first(
    client, db, auth, common_user
):
    older = add_recorda(db, common_user, song_title="Older")
    newer = add_recorda(db, common_user, song_title="Newer")
    newer.created_at = older.created_at.replace(year=older.created_at.year + 1)
    add_recorda(db, common_user, song_title="Gone", deleted_at=older.created_at)
    db.commit()

    resp = client.get(PREFIX, headers=auth)

    assert resp.status_code == 200
    assert [r["song_title"] for r in resp.json()] == ["Newer", "Older"]


def test_list_recordas_requires_auth(client):
    resp = client.get(PREFIX)
    assert resp.status_code == 401


def test_create_recorda_returns_201(client, auth, common_user):
    resp = client.post(PREFIX, json=create_payload(), headers=auth)
    assert resp.status_code == 201
    body = resp.json()
    assert uuid.UUID(body["recorda_id"])
    assert body["user_id"] == str(common_user.user_id)
    assert body["media_url"] == "/api/v1/recordas/media/abc.jpg"
    assert body["media_type"] == "PHOTO"
    assert body["song_title"] == "Song of Silence"
    assert body["deezer_track_id"] == "3135556"
    assert body["song_artist_name"] == "Disturbed"
    assert body["song_cover_url"] == "https://e.deezer.com/cover.jpg"
    assert body["song_preview_url"] == "https://cdns-preview.deezer.com/p.mp3"
    assert body["description"] == "Show incrível"
    assert body["created_at"]
    assert "deleted_at" not in body


def test_create_recorda_accepts_missing_cover_and_preview(client, auth):
    payload = create_payload()
    payload.pop("song_cover_url")
    payload.pop("song_preview_url")

    resp = client.post(PREFIX, json=payload, headers=auth)

    assert resp.status_code == 201
    assert resp.json()["song_cover_url"] == ""
    assert resp.json()["song_preview_url"] is None


def test_create_recorda_rejects_legacy_payload(client, auth):
    resp = client.post(
        PREFIX, json={"midia": "Song", "music": "Song of Silence"}, headers=auth
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "field",
    ["media_url", "deezer_track_id", "song_title", "song_artist_name", "media_type"],
)
def test_create_recorda_requires_song_snapshot(client, auth, field):
    payload = create_payload()
    payload.pop(field)
    resp = client.post(PREFIX, json=payload, headers=auth)
    assert resp.status_code == 422
    fields = resp.json()["error"]["details"]["fields"]
    assert [f["field"] for f in fields] == [field]


def test_create_recorda_rejects_unknown_media_type(client, auth):
    resp = client.post(PREFIX, json=create_payload(media_type="GIF"), headers=auth)
    assert resp.status_code == 422


def test_create_recorda_requires_auth(client):
    resp = client.post(PREFIX, json=create_payload())
    assert resp.status_code == 401


def test_get_recorda_returns_recorda(client, db, auth, common_user):
    recorda = add_recorda(db, common_user)
    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["recorda_id"] == str(recorda.recorda_id)


def test_get_recorda_returns_404_when_missing(client, auth):
    resp = client.get(f"{PREFIX}/{MISSING_ID}", headers=auth)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_get_recorda_rejects_non_uuid_id(client, auth):
    assert client.get(f"{PREFIX}/1", headers=auth).status_code == 422


def test_get_recorda_requires_auth(client):
    resp = client.get(f"{PREFIX}/{MISSING_ID}")
    assert resp.status_code == 401


def test_get_recorda_returns_author_and_likes_count(client, db, auth, common_user):
    recorda = add_recorda(db, common_user)
    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth)
    assert resp.status_code == 200
    body = resp.json()
    assert body["author"]["user_id"] == str(common_user.user_id)
    assert body["author"]["username"] == common_user.username
    assert body["deezer_track_id"] == recorda.deezer_track_id
    assert body["likes_count"] == 0
    assert "user_id" not in body


def test_get_recorda_author_can_access_own_private_recorda(client, db):
    author = add_user(db, "private_author", is_private=True)
    recorda = add_recorda(db, author)

    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(author))

    assert resp.status_code == 200
    assert resp.json()["recorda_id"] == str(recorda.recorda_id)


def test_get_recorda_accepted_follower_can_access_private_recorda(client, db):
    author = add_user(db, "private_author", is_private=True)
    follower = add_user(db, "follower")
    add_follow(db, follower, author)  # status ACCEPTED por padrão
    recorda = add_recorda(db, author)

    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(follower))

    assert resp.status_code == 200
    assert resp.json()["recorda_id"] == str(recorda.recorda_id)


def test_get_recorda_pending_follower_cannot_access_private_recorda(client, db):
    author = add_user(db, "private_author", is_private=True)
    pending_follower = add_user(db, "pending_follower")
    add_follow(db, pending_follower, author, status="PENDING")
    recorda = add_recorda(db, author)

    resp = client.get(
        f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(pending_follower)
    )

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_get_recorda_stranger_cannot_access_private_recorda(client, db):
    author = add_user(db, "private_author", is_private=True)
    stranger = add_user(db, "stranger")
    recorda = add_recorda(db, author)

    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(stranger))

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_get_recorda_public_account_is_visible_to_anyone(client, db):
    public_author = add_user(db, "public_author")  # is_private=False por padrão
    stranger = add_user(db, "another_stranger")
    recorda = add_recorda(db, public_author)

    resp = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(stranger))

    assert resp.status_code == 200
    assert resp.json()["recorda_id"] == str(recorda.recorda_id)


def test_update_recorda_changes_only_description(client, db, auth, common_user):
    recorda = add_recorda(db, common_user)
    resp = client.put(
        f"{PREFIX}/{recorda.recorda_id}",
        json={"description": "Novo texto", "song_title": "Hacked"},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Novo texto"
    assert resp.json()["song_title"] == "Song of Silence"


def test_update_recorda_returns_404_when_missing(client, auth):
    resp = client.put(f"{PREFIX}/{MISSING_ID}", json={"description": "x"}, headers=auth)
    assert resp.status_code == 404


def test_update_recorda_requires_auth(client):
    resp = client.put(f"{PREFIX}/{MISSING_ID}", json={"description": "x"})
    assert resp.status_code == 401


def test_update_recorda_of_other_user_returns_403(client, db, common_user):
    recorda = add_recorda(db, common_user)
    intruder = add_user(db, "intruder")
    resp = client.put(
        f"{PREFIX}/{recorda.recorda_id}",
        json={"description": "x"},
        headers=auth_headers(intruder),
    )
    assert resp.status_code == 403


def test_delete_recorda_soft_deletes(client, db, auth, common_user):
    recorda = add_recorda(db, common_user)

    resp = client.delete(f"{PREFIX}/{recorda.recorda_id}", headers=auth)

    assert resp.status_code == 204
    db.refresh(recorda)
    assert recorda.deleted_at is not None
    again = client.get(f"{PREFIX}/{recorda.recorda_id}", headers=auth)
    assert again.status_code == 404


def test_delete_recorda_returns_404_when_missing(client, auth):
    resp = client.delete(f"{PREFIX}/{MISSING_ID}", headers=auth)
    assert resp.status_code == 404


def test_delete_recorda_requires_auth(client):
    resp = client.delete(f"{PREFIX}/{MISSING_ID}")
    assert resp.status_code == 401


def test_delete_recorda_of_other_user_returns_403(client, db, common_user):
    recorda = add_recorda(db, common_user)
    intruder = add_user(db, "intruder")
    resp = client.delete(
        f"{PREFIX}/{recorda.recorda_id}", headers=auth_headers(intruder)
    )
    assert resp.status_code == 403
    db.refresh(recorda)
    assert recorda.deleted_at is None


def create_payload(**overrides) -> dict:
    payload = {
        "media_url": "/api/v1/recordas/media/abc.jpg",
        "media_type": "PHOTO",
        "song_title": "Song of Silence",
        "deezer_track_id": "3135556",
        "song_artist_name": "Disturbed",
        "song_cover_url": "https://e.deezer.com/cover.jpg",
        "song_preview_url": "https://cdns-preview.deezer.com/p.mp3",
        "description": "Show incrível",
    }
    payload.update(overrides)
    return payload
