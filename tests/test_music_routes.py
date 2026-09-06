import pytest
from fastapi.testclient import TestClient

from app.core.http import get_deezer_client
from app.main import app

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
            "album": {"title": "Album X", "cover_medium": "https://e.deezer.com/ax.jpg"},
            "preview": "",
            "genre_id": None,
        },
    ]
}


class FakeDeezerClient:
    def __init__(self, responses: dict):
        self._responses = responses

    def get(self, path: str, **kwargs):
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
        {"/genre": GENRES_RESPONSE, "/search/artist": ARTISTS_RESPONSE, "/search": TRACKS_RESPONSE}
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
