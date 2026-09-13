from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.core.http import get_deezer_client
from app.main import app
from app.services import music_service

GENRES_RESPONSE = {
    "data": [
        {"id": 0, "name": "All", "picture": "", "picture_medium": ""},
        {"id": 132, "name": "Pop", "picture_medium": "https://e.deezer.com/pop.jpg"},
        {"id": 116, "name": "Rap", "picture_medium": "https://e.deezer.com/rap.jpg"},
    ]
}

ARTISTS_RESPONSE = {
    "data": [
        {"id": 1, "name": "Eminem", "picture_medium": "https://e.deezer.com/em.jpg"},
    ]
}

TRACKS_RESPONSE = {
    "data": [
        {
            "id": 10,
            "title": "Lose Yourself",
            "artist": {"name": "Eminem"},
            "album": {"title": "8 Mile", "cover_medium": "https://e.deezer.com/8m.jpg"},
            "preview": "https://cdns-preview.dzcdn.net/lose.mp3",
            "genre_id": 116,
        },
        {
            "id": 11,
            "title": "No Preview Track",
            "artist": {"name": "Artist X"},
            "album": {
                "title": "Album X",
                "cover_medium": "https://e.deezer.com/ax.jpg",
            },
            "preview": "",
            "genre_id": None,
        },
    ]
}


class FakeDeezerClient:
    def __init__(self, responses: dict):
        self._responses = responses
        self.calls: list[tuple[str, dict]] = []

    def get(self, path: str, **kwargs):
        self.calls.append((path, kwargs.get("params") or {}))
        return FakeResponse(self._responses.get(path, {"data": []}))


class FakeResponse:
    def __init__(self, body: dict):
        self._body = body
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


class FakeErrorClient:
    def get(self, path: str, **kwargs):
        import httpx

        raise httpx.TimeoutException("timeout")


@pytest.fixture
def music_client():
    fake = FakeDeezerClient(
        {
            "/genre": GENRES_RESPONSE,
            "/search/artist": ARTISTS_RESPONSE,
            "/search": TRACKS_RESPONSE,
        }
    )

    def _override():
        yield fake

    app.dependency_overrides[get_deezer_client] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_deezer_client, None)


@pytest.fixture
def error_client():
    def _override():
        yield FakeErrorClient()

    app.dependency_overrides[get_deezer_client] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_deezer_client, None)


def test_genres_returns_list(music_client: TestClient):
    resp = music_client.get("/api/v1/music/genres")
    assert resp.status_code == 200
    data = resp.json()
    # genre id=0 ("All") is filtered out
    assert len(data) == 2
    assert data[0]["id"] == 132
    assert data[0]["name"] == "Pop"
    assert "picture_url" in data[0]


def test_genres_deezer_unavailable(error_client: TestClient):
    resp = error_client.get("/api/v1/music/genres")
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "BAD_GATEWAY"


def test_artists_search(music_client: TestClient):
    resp = music_client.get("/api/v1/music/artists/search", params={"q": "Eminem"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Eminem"


def test_artists_search_ranks_exact_match_before_more_popular_tributes():
    data = [
        artist(1, "Queen Tribute Band", nb_fan=900_000),
        artist(2, "Queens of the Stone Age", nb_fan=2_000_000),
        artist(3, "Queen", nb_fan=12_000_000),
        artist(4, "The Queen Tribute", nb_fan=5_000),
        artist(5, "Dancing Queen Orchestra", nb_fan=10),
        artist(6, "Freddie Mercury", nb_fan=3_000_000),
    ]

    ranked = rank_names(data, "queen")

    assert ranked[0] == "Queen"
    assert ranked[1:3] == ["Queens of the Stone Age", "Queen Tribute Band"]
    assert ranked[-1] == "Freddie Mercury"


def test_artists_search_ignores_case_and_accents():
    data = [
        artist(1, "Anitta Cover", nb_fan=100),
        artist(2, "ANITTÁ", nb_fan=50),
    ]

    assert rank_names(data, "anitta") == ["ANITTÁ", "Anitta Cover"]


def test_artists_search_breaks_ties_by_fans_then_deezer_order():
    data = [
        artist(1, "Eminem Karaoke", nb_fan=10),
        artist(2, "Eminem Tribute", nb_fan=500),
        artist(3, "Eminem Covers", nb_fan=10),
    ]

    assert rank_names(data, "eminem") == [
        "Eminem Tribute",
        "Eminem Karaoke",
        "Eminem Covers",
    ]


def test_artists_search_removes_duplicates_and_limits_results():
    data = (
        [artist(1, "Djavan")]
        + [artist(i, f"Artist {i}") for i in range(2, 60)]
        + [artist(1, "Djavan")]
    )

    ranked = music_service.rank_artists(data, "djavan")[
        : music_service.ARTIST_SEARCH_RESULT_LIMIT
    ]

    assert [a["id"] for a in ranked].count(1) == 1
    assert len(ranked) == music_service.ARTIST_SEARCH_RESULT_LIMIT


def test_artists_search_endpoint_returns_ranked_results():
    fake = FakeDeezerClient(
        {
            "/search/artist": {
                "data": [
                    artist(1, "Legião Urbana Cover", nb_fan=1),
                    artist(2, "Legião Urbana", nb_fan=1_000_000),
                ]
            }
        }
    )

    with deezer_override(fake) as c:
        resp = c.get("/api/v1/music/artists/search", params={"q": "legiao urbana"})

    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [2, 1]
    assert fake.calls == [
        (
            "/search/artist",
            {"q": "legiao urbana", "limit": music_service.ARTIST_SEARCH_FETCH_LIMIT},
        )
    ]


def test_normalize_strips_accents_case_and_extra_spaces():
    assert music_service.normalize("  Legião   URBANA ") == "legiao urbana"


def test_artists_search_missing_q(music_client: TestClient):
    resp = music_client.get("/api/v1/music/artists/search")
    assert resp.status_code == 422


def test_artists_search_whitespace_q(music_client: TestClient):
    resp = music_client.get("/api/v1/music/artists/search", params={"q": "   "})
    assert resp.status_code == 200
    assert resp.json() == []


def test_artists_search_deezer_unavailable(error_client: TestClient):
    resp = error_client.get("/api/v1/music/artists/search", params={"q": "Eminem"})
    assert resp.status_code == 502


def test_tracks_search(music_client: TestClient):
    resp = music_client.get("/api/v1/music/tracks/search", params={"q": "Lose"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "Lose Yourself"
    assert data[0]["preview_url"] == "https://cdns-preview.dzcdn.net/lose.mp3"
    # track without preview has preview_url null
    assert data[1]["preview_url"] is None


def test_tracks_search_lifts_exact_matches_and_removes_duplicates():
    data = [
        track(1, "Hello Remix", "DJ X"),
        track(2, "Someone Like You", "Adele"),
        track(3, "Hello", "Adele"),
        track(4, "hello", "ADELE"),
        track(5, "Say Hello", "Band"),
    ]

    ranked = music_service.rank_tracks(data, "hello")

    assert [t["id"] for t in ranked] == [3, 1, 2, 5]


def test_tracks_search_keeps_deezer_order_without_strong_matches():
    data = [track(1, "Song A", "Artist"), track(2, "Song B", "Artist")]

    assert [t["id"] for t in music_service.rank_tracks(data, "album name")] == [1, 2]


def test_tracks_search_missing_q(music_client: TestClient):
    resp = music_client.get("/api/v1/music/tracks/search")
    assert resp.status_code == 422


def test_tracks_search_whitespace_q(music_client: TestClient):
    resp = music_client.get("/api/v1/music/tracks/search", params={"q": "  "})
    assert resp.status_code == 200
    assert resp.json() == []


def test_tracks_search_deezer_unavailable(error_client: TestClient):
    resp = error_client.get("/api/v1/music/tracks/search", params={"q": "test"})
    assert resp.status_code == 502


def artist(id: int, name: str, nb_fan: int = 0) -> dict:
    return {"id": id, "name": name, "nb_fan": nb_fan, "picture_medium": None}


def track(id: int, title: str, artist_name: str) -> dict:
    return {
        "id": id,
        "title": title,
        "artist": {"name": artist_name},
        "album": {"title": "Album", "cover_medium": None},
        "preview": "",
        "genre_id": None,
    }


def rank_names(data: list[dict], q: str) -> list[str]:
    return [a["name"] for a in music_service.rank_artists(data, q)]


@contextmanager
def deezer_override(fake):
    def _override():
        yield fake

    app.dependency_overrides[get_deezer_client] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_deezer_client, None)
