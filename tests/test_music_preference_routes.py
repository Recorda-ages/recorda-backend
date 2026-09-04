"""Endpoint tests for the onboarding music preferences under /api/v1/users/me."""

from app.core import security
from app.core.config import settings
from app.models import MusicPreference, User

URL = "/api/v1/users/me/music-preferences"

GENRES = [
    {"deezer_id": 132, "name": "Pop"},
    {"deezer_id": 152, "name": "Rock"},
    {"deezer_id": 116, "name": "Rap/Hip Hop"},
]
ARTISTS = [
    {"deezer_id": 27, "name": "Daft Punk"},
    {"deezer_id": 13, "name": "Eminem"},
    {"deezer_id": 145, "name": "Coldplay"},
]
TRACK = {"deezer_id": 3135556, "name": "Harder, Better, Faster, Stronger"}


def body(**overrides) -> dict:
    payload = {"genres": GENRES, "artists": ARTISTS, "favorite_track": TRACK}
    payload.update(overrides)
    return payload


def authenticate(db, monkeypatch, username: str = "alice") -> tuple[User, dict]:
    """Persist a user and return it alongside its Bearer auth header."""
    monkeypatch.setattr(settings, "password_hash_iterations", 1)
    user = User(
        name=username.title(),
        email=f"{username}@example.com",
        username=username,
        password_hash=security.hash_password("correct"),
        account_type="common",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(
        subject=str(user.id),
        additional_claims={"username": username, "account_type": "common"},
    )
    return user, {"Authorization": f"Bearer {token}"}


def test_saves_preferences_and_completes_onboarding(
    sqlite_client, sqlite_db, monkeypatch
):
    user, headers = authenticate(sqlite_db, monkeypatch)

    resp = sqlite_client.post(URL, json=body(), headers=headers)

    assert resp.status_code == 200
    saved = resp.json()
    assert [g["name"] for g in saved["genres"]] == ["Pop", "Rock", "Rap/Hip Hop"]
    assert [a["deezer_id"] for a in saved["artists"]] == [27, 13, 145]
    assert saved["favorite_track"]["name"] == "Harder, Better, Faster, Stronger"
    assert saved["onboarding_completed"] is True

    sqlite_db.refresh(user)
    assert user.onboarding_completed is True
    stored = sqlite_db.query(MusicPreference).filter_by(user_id=user.id).all()
    assert sorted(p.kind for p in stored) == (
        ["artist"] * 3 + ["genre"] * 3 + ["track"]
    )
    assert {p.deezer_id for p in stored if p.kind == "genre"} == {132, 152, 116}
    assert {p.deezer_id for p in stored if p.kind == "artist"} == {27, 13, 145}
    track = next(p for p in stored if p.kind == "track")
    assert (track.deezer_id, track.name) == (
        3135556,
        "Harder, Better, Faster, Stronger",
    )


def test_rejects_fewer_than_three_artists(sqlite_client, sqlite_db, monkeypatch):
    _, headers = authenticate(sqlite_db, monkeypatch)

    resp = sqlite_client.post(URL, json=body(artists=ARTISTS[:2]), headers=headers)

    assert resp.status_code == 422


def test_rejects_fewer_than_three_genres(sqlite_client, sqlite_db, monkeypatch):
    _, headers = authenticate(sqlite_db, monkeypatch)

    resp = sqlite_client.post(URL, json=body(genres=GENRES[:2]), headers=headers)

    assert resp.status_code == 422


def test_rejects_missing_favorite_track(sqlite_client, sqlite_db, monkeypatch):
    _, headers = authenticate(sqlite_db, monkeypatch)
    payload = body()
    del payload["favorite_track"]

    resp = sqlite_client.post(URL, json=payload, headers=headers)

    assert resp.status_code == 422


def test_rejects_repeated_items_padding_the_minimum(
    sqlite_client, sqlite_db, monkeypatch
):
    _, headers = authenticate(sqlite_db, monkeypatch)
    repeated = [ARTISTS[0], ARTISTS[1], dict(ARTISTS[0], name="Daft Punk (dup)")]

    resp = sqlite_client.post(URL, json=body(artists=repeated), headers=headers)

    assert resp.status_code == 422


def test_second_call_replaces_previous_preferences(
    sqlite_client, sqlite_db, monkeypatch
):
    user, headers = authenticate(sqlite_db, monkeypatch)
    sqlite_client.post(URL, json=body(), headers=headers)

    new_genres = [
        {"deezer_id": 165, "name": "R&B"},
        {"deezer_id": 129, "name": "Jazz"},
        {"deezer_id": 106, "name": "Electro"},
    ]
    resp = sqlite_client.post(URL, json=body(genres=new_genres), headers=headers)

    assert resp.status_code == 200
    assert [g["name"] for g in resp.json()["genres"]] == ["R&B", "Jazz", "Electro"]
    stored = sqlite_db.query(MusicPreference).filter_by(user_id=user.id).all()
    assert len(stored) == 7
    assert {p.name for p in stored if p.kind == "genre"} == {"R&B", "Jazz", "Electro"}


def test_preferences_are_scoped_to_the_authenticated_user(
    sqlite_client, sqlite_db, monkeypatch
):
    alice, alice_headers = authenticate(sqlite_db, monkeypatch, username="alice")
    bob, bob_headers = authenticate(sqlite_db, monkeypatch, username="bob")
    sqlite_client.post(URL, json=body(), headers=alice_headers)

    sqlite_client.post(URL, json=body(), headers=bob_headers)

    assert sqlite_db.query(MusicPreference).filter_by(user_id=alice.id).count() == 7
    assert sqlite_db.query(MusicPreference).filter_by(user_id=bob.id).count() == 7
    sqlite_db.refresh(alice)
    assert alice.onboarding_completed is True


def test_requires_authentication(sqlite_client, sqlite_db):
    resp = sqlite_client.post(URL, json=body())

    assert resp.status_code == 401
    assert sqlite_db.query(MusicPreference).count() == 0


def test_rejects_duplicate_beyond_the_minimum(sqlite_client, sqlite_db, monkeypatch):
    """Three distinct plus a repeat used to slip past validation and 500 on insert."""
    _, headers = authenticate(sqlite_db, monkeypatch)
    with_repeat = [*ARTISTS, dict(ARTISTS[0], name="Daft Punk (dup)")]

    resp = sqlite_client.post(URL, json=body(artists=with_repeat), headers=headers)

    assert resp.status_code == 422
    assert sqlite_db.query(MusicPreference).count() == 0


def test_rejects_oversized_selection(sqlite_client, sqlite_db, monkeypatch):
    _, headers = authenticate(sqlite_db, monkeypatch)
    too_many = [{"deezer_id": i, "name": f"Genre {i}"} for i in range(1, 60)]

    resp = sqlite_client.post(URL, json=body(genres=too_many), headers=headers)

    assert resp.status_code == 422


def test_rejects_malformed_items(sqlite_client, sqlite_db, monkeypatch):
    _, headers = authenticate(sqlite_db, monkeypatch)
    blank = [*ARTISTS[:2], {"deezer_id": 99, "name": ""}]
    non_positive = [*GENRES[:2], {"deezer_id": 0, "name": "Zero"}]

    assert (
        sqlite_client.post(URL, json=body(artists=blank), headers=headers).status_code
        == 422
    )
    assert (
        sqlite_client.post(
            URL, json=body(genres=non_positive), headers=headers
        ).status_code
        == 422
    )
