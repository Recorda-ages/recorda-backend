"""Endpoint tests for the User API under /api/v1/users."""

import uuid

import pytest

from app.core import security
from app.core.config import settings
from app.core.time import now_utc  # ← novo
from app.models import AppUser
from app.models.app_user import ROLE_ADMIN, ROLE_USER, STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING  # ← novo
from tests.factories import add_follow, add_recorda, add_user, auth_headers

PREFIX = "/api/v1/users"
MISSING_ID = uuid.uuid4()


@pytest.fixture
def admin_headers(db):
    return auth_headers(add_user(db, "admin", role=ROLE_ADMIN))


def test_list_users_requires_admin_and_returns_records(client, admin_headers):
    resp = client.get(PREFIX, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Admin"
    assert body[0]["email"] == "admin@example.com"
    assert body[0]["role"] == ROLE_ADMIN


def test_own_profile_requires_authentication(client):
    response = client.get(f"{PREFIX}/me/profile")

    assert response.status_code == 401


def test_own_profile_rejects_incomplete_onboarding(client, db):
    user = add_user(db, "incomplete")

    response = client.get(f"{PREFIX}/me/profile", headers=auth_headers(user))

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Complete o onboarding musical para acessar o perfil."
    )


FAVORITE_SONG = {
    "fav_song_deezer_track_id": "3135556",
    "fav_song_title": "Harder, Better, Faster, Stronger",
    "fav_song_artist_name": "Daft Punk",
    "fav_song_cover_url": "https://e.deezer.com/cover.jpg",
    "fav_song_preview_url": "https://cdns-preview.deezer.com/p.mp3",
}


def test_own_profile_returns_profile_header(client, db):
    user = add_user(db, "gabi", **FAVORITE_SONG)
    add_recorda(db, user)
    add_follow(db, add_user(db, "fan"), user)

    response = client.get(f"{PREFIX}/me/profile", headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "gabi"
    assert body["name"] == user.name
    assert body["profile_picture_url"] is None
    assert body["is_private"] is False
    assert body["counts"] == {"recordas": 1, "followers": 1, "following": 0}
    assert body["favorite_song"]["deezer_track_id"] == "3135556"
    assert body["relationship"] == {
        "is_self": True,
        "follow_status": "nenhuma",
        "follow_id": None,
    }
    assert body["can_view_content"] is True
    assert body["streak"] == {"current_days": 1, "published_today": True}


def test_own_profile_no_longer_embeds_lists_or_private_fields(client, db):
    user = add_user(db, "gabi", **FAVORITE_SONG)

    body = client.get(f"{PREFIX}/me/profile", headers=auth_headers(user)).json()

    removed = {"favorite_genres", "favorite_artists", "recordas"}
    private = {"email", "role", "status"}
    assert not (removed | private) & body.keys()


def test_own_profile_rejects_token_issued_before_suspension(client, db):
    user = add_user(db, "suspended")
    headers = auth_headers(user)
    user.status = STATUS_SUSPENDED
    db.commit()

    response = client.get(f"{PREFIX}/me/profile", headers=headers)

    assert response.status_code == 401


def _profile_url(user_id) -> str:
    return f"{PREFIX}/{user_id}/profile"


def test_third_party_profile_requires_authentication(client, db):
    owner = add_user(db, "dono", **FAVORITE_SONG)

    assert client.get(_profile_url(owner.user_id)).status_code == 401


def test_third_party_profile_shows_public_profile(client, db):
    owner = add_user(db, "dono", **FAVORITE_SONG)
    add_recorda(db, owner)
    viewer = add_user(db, "visitante")

    response = client.get(_profile_url(owner.user_id), headers=auth_headers(viewer))

    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {"recordas": 1, "followers": 0, "following": 0}
    assert body["can_view_content"] is True
    assert body["relationship"] == {
        "is_self": False,
        "follow_status": "nenhuma",
        "follow_id": None,
    }


def test_third_party_profile_hides_counts_while_request_is_pending(client, db):
    owner = add_user(db, "dono", is_private=True, **FAVORITE_SONG)
    viewer = add_user(db, "visitante")
    follow = add_follow(db, viewer, owner, status=STATUS_PENDING)

    body = client.get(_profile_url(owner.user_id), headers=auth_headers(viewer)).json()

    assert body["relationship"]["follow_status"] == "solicitado"
    assert body["relationship"]["follow_id"] == str(follow.follow_id)
    assert body["counts"] is None
    assert body["can_view_content"] is False
    assert body["favorite_song"]["deezer_track_id"] == "3135556"
    assert body["streak"] is not None


def test_third_party_profile_shows_private_profile_to_accepted_follower(client, db):
    owner = add_user(db, "dono", is_private=True, **FAVORITE_SONG)
    viewer = add_user(db, "visitante")
    add_follow(db, viewer, owner)

    body = client.get(_profile_url(owner.user_id), headers=auth_headers(viewer)).json()

    assert body["relationship"]["follow_status"] == "seguindo"
    assert body["counts"] is not None
    assert body["can_view_content"] is True


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"status": STATUS_SUSPENDED}, id="suspenso"),
        pytest.param({"deleted_at": now_utc()}, id="excluido"),
        pytest.param({}, id="sem-onboarding"),
    ],
)
def test_third_party_profile_returns_404_for_unavailable_owner(client, db, fields):
    song = {} if not fields else FAVORITE_SONG
    owner = add_user(db, "dono", **song, **fields)
    viewer = add_user(db, "visitante")

    response = client.get(_profile_url(owner.user_id), headers=auth_headers(viewer))

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Usuário não encontrado."


def test_third_party_profile_returns_404_for_missing_user(client, db):
    viewer = add_user(db, "visitante")

    response = client.get(_profile_url(MISSING_ID), headers=auth_headers(viewer))

    assert response.status_code == 404


def test_third_party_profile_of_self_matches_own_profile(client, db):
    user = add_user(db, "gabi", **FAVORITE_SONG)
    headers = auth_headers(user)

    by_id = client.get(_profile_url(user.user_id), headers=headers).json()
    own = client.get(f"{PREFIX}/me/profile", headers=headers).json()

    assert by_id == own
    assert by_id["relationship"]["is_self"] is True


def test_third_party_profile_of_self_rejects_incomplete_onboarding(client, db):
    user = add_user(db, "incomplete")

    response = client.get(_profile_url(user.user_id), headers=auth_headers(user))

    assert response.status_code == 409


def test_third_party_profile_applies_privacy_change_immediately(client, db):
    owner = add_user(db, "dono", **FAVORITE_SONG)
    headers = auth_headers(add_user(db, "visitante"))
    assert client.get(_profile_url(owner.user_id), headers=headers).json()["counts"]

    owner.is_private = True
    db.commit()

    body = client.get(_profile_url(owner.user_id), headers=headers).json()
    assert body["counts"] is None
    assert body["can_view_content"] is False


def test_third_party_profile_never_exposes_private_fields(client, db):
    owner = add_user(db, "dono", **FAVORITE_SONG)
    viewer = add_user(db, "visitante")

    body = client.get(_profile_url(owner.user_id), headers=auth_headers(viewer)).json()

    assert not {"email", "role", "status"} & body.keys()


def test_list_users_returns_all_records(client, db, admin_headers):
    add_user(db, "alice", name="A")
    resp = client.get(PREFIX, headers=admin_headers)
    assert resp.status_code == 200
    assert {u["name"] for u in resp.json()} == {"A", "Admin"}


def test_list_users_hides_soft_deleted(client, db, admin_headers):
    alice = add_user(db, "alice")
    alice.deleted_at = alice.created_at
    db.commit()
    resp = client.get(PREFIX, headers=admin_headers)
    assert [u["username"] for u in resp.json()] == ["admin"]


def test_create_user_returns_201_and_hashes_password(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    resp = client.post(
        PREFIX,
        json={
            "name": "A",
            "email": "a@e.com",
            "username": "alice",
            "password": "secret",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "A"

    stored = db.get(AppUser, uuid.UUID(body["user_id"]))
    assert stored.username == "alice"
    assert stored.role == ROLE_USER
    assert stored.password_hash != "secret"
    assert security.verify_password("secret", stored.password_hash) is True
    assert security.verify_password("wrong", stored.password_hash) is False


def test_create_user_with_taken_username_returns_409(client, db, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    payload = {
        "name": "A",
        "email": "a@e.com",
        "username": "alice",
        "password": "secret",
    }
    assert client.post(PREFIX, json=payload).status_code == 201

    resp = client.post(PREFIX, json={**payload, "email": "other@e.com"})

    assert resp.status_code == 409
    fields = resp.json()["error"]["details"]["fields"]
    assert [f["field"] for f in fields] == ["username"]
    assert db.query(AppUser).count() == 1


def test_create_user_validates_missing_field(client):
    resp = client.post(PREFIX, json={"name": "A"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_user_does_not_expose_password(client, monkeypatch):
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    resp = client.post(
        PREFIX,
        json={
            "name": "A",
            "email": "a@e.com",
            "username": "alice",
            "password": "secret",
        },
    )
    body = resp.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert "hashed_password" not in body


def test_get_user_returns_user(client, db, admin_headers):
    alice = add_user(db, "alice", name="A")
    resp = client.get(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "A"
    assert resp.json()["user_id"] == str(alice.user_id)


def test_get_user_returns_404_when_missing(client, admin_headers):
    resp = client.get(f"{PREFIX}/{MISSING_ID}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_get_user_rejects_non_uuid_id(client, admin_headers):
    resp = client.get(f"{PREFIX}/1", headers=admin_headers)
    assert resp.status_code == 422


def test_update_user_returns_200(client, db, admin_headers):
    alice = add_user(db, "alice", name="A", email="a@e.com")
    resp = client.put(
        f"{PREFIX}/{alice.user_id}", json={"name": "B"}, headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "B"
    assert resp.json()["email"] == "a@e.com"


def test_update_user_returns_404_when_missing(client, admin_headers):
    resp = client.put(
        f"{PREFIX}/{MISSING_ID}", json={"name": "B"}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_delete_user_soft_deletes(client, db, admin_headers):
    alice = add_user(db, "alice")
    resp = client.delete(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert resp.status_code == 204
    db.refresh(alice)
    assert alice.deleted_at is not None
    again = client.get(f"{PREFIX}/{alice.user_id}", headers=admin_headers)
    assert again.status_code == 404


def test_delete_user_returns_404_when_missing(client, admin_headers):
    resp = client.delete(f"{PREFIX}/{MISSING_ID}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.parametrize("role", [ROLE_ADMIN, ROLE_USER])
def test_change_role(client, db, admin_headers, role):
    alice = add_user(db, "alice")
    resp = client.patch(
        f"{PREFIX}/{alice.user_id}/role", json={"role": role}, headers=admin_headers
    )
    assert resp.status_code == 200
    db.refresh(alice)
    assert alice.role == role


def test_change_role_returns_404_when_missing(client, admin_headers):
    resp = client.patch(
        f"{PREFIX}/{MISSING_ID}/role", json={"role": ROLE_ADMIN}, headers=admin_headers
    )
    assert resp.status_code == 404


def test_change_role_rejects_invalid_value(client, db, admin_headers):
    alice = add_user(db, "alice")
    resp = client.patch(
        f"{PREFIX}/{alice.user_id}/role",
        json={"role": "superuser"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_change_role_requires_admin(client, db):
    alice = add_user(db, "alice")
    resp = client.patch(f"{PREFIX}/{alice.user_id}/role", json={"role": ROLE_ADMIN})
    assert resp.status_code == 401
