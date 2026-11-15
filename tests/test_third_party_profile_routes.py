"""Testes dos extras do perfil de terceiros: músicas favoritas e métricas por usuário."""

import uuid

import pytest

from app.core.time import now_utc
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from tests.factories import add_follow, add_recorda, add_user, auth_headers

GENRES = [
    {"deezer_id": 132, "name": "Pop"},
    {"deezer_id": 152, "name": "Rock"},
    {"deezer_id": 116, "name": "Rap/Hip Hop"},
]
ARTISTS = [
    {
        "deezer_id": 27,
        "name": "Daft Punk",
        "picture_url": "https://e.deezer.com/dp.jpg",
    },
    {"deezer_id": 13, "name": "Eminem"},
    {"deezer_id": 145, "name": "Coldplay"},
]
TRACK = {
    "deezer_id": 3135556,
    "title": "Harder, Better, Faster, Stronger",
    "artist_name": "Daft Punk",
    "cover_url": "https://e.deezer.com/cover.jpg",
}


def save_preferences(client, user) -> None:
    response = client.post(
        "/api/v1/users/me/music-preferences",
        json={"genres": GENRES, "artists": ARTISTS, "favorite_track": TRACK},
        headers=auth_headers(user),
    )
    assert response.status_code == 200


def tastes_url(user) -> str:
    return f"/api/v1/users/{user.user_id}/music-preferences"


def metrics_url(user, query: str = "") -> str:
    return f"/api/v1/users/{user.user_id}/metrics{query}"


ROUTES = pytest.mark.parametrize(
    "build_url", [tastes_url, metrics_url], ids=["tastes", "metrics"]
)


class TestAccess:
    @ROUTES
    def test_requires_authentication(self, client, db, build_url):
        owner = add_user(db, "owner")

        assert client.get(build_url(owner)).status_code == 401

    @ROUTES
    @pytest.mark.parametrize("state", ["unknown", "deleted", "suspended"])
    def test_unavailable_owner_returns_404(self, client, db, build_url, state):
        viewer = add_user(db, "viewer")
        owner = {
            "unknown": None,
            "deleted": add_user(db, "ghost", deleted_at=now_utc()),
            "suspended": add_user(db, "banned", status=STATUS_SUSPENDED),
        }[state]
        url = (
            build_url(owner)
            if owner
            else build_url(type("U", (), {"user_id": uuid.uuid4()}))
        )

        response = client.get(url, headers=auth_headers(viewer))

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Usuário não encontrado."

    @ROUTES
    def test_private_account_without_follow_returns_403(self, client, db, build_url):
        owner = add_user(db, "owner", is_private=True)
        viewer = add_user(db, "viewer")

        response = client.get(build_url(owner), headers=auth_headers(viewer))

        assert response.status_code == 403
        assert response.json()["error"]["message"] == "Esta conta é privada."

    @ROUTES
    def test_private_account_with_pending_request_returns_403(
        self, client, db, build_url
    ):
        owner = add_user(db, "owner", is_private=True)
        viewer = add_user(db, "viewer")
        add_follow(db, viewer, owner, status=STATUS_PENDING)

        response = client.get(build_url(owner), headers=auth_headers(viewer))

        assert response.status_code == 403

    @ROUTES
    def test_private_account_with_accepted_follow_returns_200(
        self, client, db, build_url
    ):
        owner = add_user(db, "owner", is_private=True)
        viewer = add_user(db, "viewer")
        add_follow(db, viewer, owner)

        assert (
            client.get(build_url(owner), headers=auth_headers(viewer)).status_code
            == 200
        )

    @ROUTES
    def test_owner_sees_own_data_even_when_private(self, client, db, build_url):
        owner = add_user(db, "owner", is_private=True)

        assert (
            client.get(build_url(owner), headers=auth_headers(owner)).status_code == 200
        )

    @ROUTES
    def test_malformed_user_id_returns_422(self, client, db, build_url):
        viewer = add_user(db, "viewer")
        url = build_url(type("U", (), {"user_id": "not-a-uuid"}))

        assert client.get(url, headers=auth_headers(viewer)).status_code == 422


class TestMusicTastes:
    def test_returns_artists_and_genres_without_the_favorite_track(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        save_preferences(client, owner)

        response = client.get(tastes_url(owner), headers=auth_headers(viewer))

        body = response.json()
        assert set(body) == {"artists", "genres"}
        assert {a["name"] for a in body["artists"]} == {
            "Daft Punk",
            "Eminem",
            "Coldplay",
        }
        assert {g["name"] for g in body["genres"]} == {"Pop", "Rock", "Rap/Hip Hop"}
        daft = next(a for a in body["artists"] if a["name"] == "Daft Punk")
        assert daft == {
            "deezer_id": 27,
            "name": "Daft Punk",
            "picture_url": "https://e.deezer.com/dp.jpg",
        }

    def test_returns_empty_lists_without_preferences(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")

        response = client.get(tastes_url(owner), headers=auth_headers(viewer))

        assert response.json() == {"artists": [], "genres": []}

    def test_me_route_keeps_working(self, client, db):
        owner = add_user(db, "owner")
        save_preferences(client, owner)

        response = client.get(
            "/api/v1/users/me/music-preferences", headers=auth_headers(owner)
        )

        assert response.status_code == 200
        assert response.json()["favorite_track"]["title"] == TRACK["title"]


class TestUserMetrics:
    def test_returns_the_owners_metrics_not_the_viewers(self, client, db):
        owner = add_user(db, "owner")
        viewer = add_user(db, "viewer")
        add_recorda(db, owner, song_artist_name="Daft Punk")
        add_recorda(db, viewer, song_artist_name="Disturbed")

        response = client.get(
            metrics_url(owner, "?bundle=profile&period=all_time"),
            headers=auth_headers(viewer),
        )

        body = response.json()
        assert response.status_code == 200
        assert body["period"] == "all_time"
        assert body["top_artist"]["artist_name"] == "Daft Punk"
        assert body["streak"]["current_streak_days"] == 1

    def test_same_payload_as_the_own_route_for_the_owner(self, client, db):
        owner = add_user(db, "owner")
        add_recorda(db, owner)

        own = client.get("/api/v1/users/me/metrics", headers=auth_headers(owner))
        by_id = client.get(metrics_url(owner), headers=auth_headers(owner))

        assert by_id.json() == own.json()

    def test_rejects_invalid_period(self, client, db):
        owner = add_user(db, "owner")

        response = client.get(
            metrics_url(owner, "?period=forever"), headers=auth_headers(owner)
        )

        assert response.status_code == 422

    def test_me_route_is_not_shadowed(self, client, db):
        owner = add_user(db, "owner")

        response = client.get("/api/v1/users/me/metrics", headers=auth_headers(owner))

        assert response.status_code == 200
