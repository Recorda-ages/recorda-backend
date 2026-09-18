"""Endpoint tests for the onboarding music preferences under /api/v1/users/me."""

from sqlalchemy import select

from app.db.seed_data import GENRE_SEED
from app.models import Genre, UserFavoriteArtist, UserFavoriteGenre
from tests.factories import add_user, auth_headers

URL = "/api/v1/users/me/music-preferences"

GENRES = [
    {"deezer_id": 132, "name": "Pop", "picture_url": "https://e.deezer.com/pop.jpg"},
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
    "preview_url": "https://cdns-preview.deezer.com/p.mp3",
}


def body(**overrides) -> dict:
    payload = {"genres": GENRES, "artists": ARTISTS, "favorite_track": TRACK}
    payload.update(overrides)
    return payload


def authenticate(db, username: str = "alice"):
    user = add_user(db, username)
    return user, auth_headers(user)


def favorite_genre_names(db, user) -> set[str]:
    stmt = (
        select(Genre.name)
        .join(UserFavoriteGenre, UserFavoriteGenre.genre_id == Genre.genre_id)
        .where(UserFavoriteGenre.user_id == user.user_id)
    )
    return set(db.scalars(stmt))


def favorite_artists(db, user) -> list[UserFavoriteArtist]:
    return db.query(UserFavoriteArtist).filter_by(user_id=user.user_id).all()


def test_saves_preferences_and_completes_onboarding(client, db):
    user, headers = authenticate(db)

    resp = client.post(URL, json=body(), headers=headers)

    assert resp.status_code == 200
    saved = resp.json()
    assert [g["name"] for g in saved["genres"]] == ["Pop", "Rock", "Rap/Hip Hop"]
    assert [a["deezer_id"] for a in saved["artists"]] == [27, 13, 145]
    assert saved["favorite_track"]["title"] == "Harder, Better, Faster, Stronger"
    assert saved["onboarding_completed"] is True

    db.refresh(user)
    assert user.onboarding_completed is True
    assert user.fav_song_deezer_track_id == "3135556"
    assert user.fav_song_title == "Harder, Better, Faster, Stronger"
    assert user.fav_song_artist_name == "Daft Punk"
    assert user.fav_song_cover_url == "https://e.deezer.com/cover.jpg"
    assert user.fav_song_preview_url == "https://cdns-preview.deezer.com/p.mp3"

    assert favorite_genre_names(db, user) == {"Pop", "Rock", "Rap/Hip Hop"}
    artists = {a.deezer_artist_id: a for a in favorite_artists(db, user)}
    assert set(artists) == {"27", "13", "145"}
    assert artists["27"].artist_name == "Daft Punk"
    assert artists["27"].artist_image_url == "https://e.deezer.com/dp.jpg"
    assert all(a.selected_at is not None for a in artists.values())


def test_reuses_seeded_genres_matching_by_name(client, db):
    _, headers = authenticate(db)
    seeded_pop = dict((name, gid) for gid, name in GENRE_SEED)["Pop"]

    client.post(URL, json=body(), headers=headers)

    pop = db.get(Genre, seeded_pop)
    assert pop.deezer_genre_id == "132"
    assert pop.picture_url == "https://e.deezer.com/pop.jpg"
    assert db.query(Genre).filter_by(name="Pop").count() == 1


def test_creates_genre_rows_for_deezer_genres_outside_the_seed(client, db):
    _, headers = authenticate(db)

    client.post(URL, json=body(), headers=headers)

    rap = db.query(Genre).filter_by(name="Rap/Hip Hop").one()
    assert rap.deezer_genre_id == "116"
    assert db.query(Genre).count() == len(GENRE_SEED) + 1


def test_reuses_genre_by_deezer_id_across_users(client, db):
    _, alice = authenticate(db, "alice")
    _, bob = authenticate(db, "bob")

    client.post(URL, json=body(), headers=alice)
    client.post(URL, json=body(), headers=bob)

    assert db.query(Genre).filter_by(deezer_genre_id="116").count() == 1


def test_accepts_track_without_cover_or_preview(client, db):
    user, headers = authenticate(db)
    track = {k: TRACK[k] for k in ("deezer_id", "title", "artist_name")}

    resp = client.post(URL, json=body(favorite_track=track), headers=headers)

    assert resp.status_code == 200
    db.refresh(user)
    assert user.fav_song_cover_url == ""
    assert user.fav_song_preview_url is None


def test_rejects_legacy_favorite_track_shape(client, db):
    _, headers = authenticate(db)
    legacy = {"deezer_id": 3135556, "name": "Harder, Better, Faster, Stronger"}

    resp = client.post(URL, json=body(favorite_track=legacy), headers=headers)

    assert resp.status_code == 422


def test_rejects_fewer_than_three_artists(client, db):
    _, headers = authenticate(db)
    resp = client.post(URL, json=body(artists=ARTISTS[:2]), headers=headers)
    assert resp.status_code == 422


def test_rejects_fewer_than_three_genres(client, db):
    _, headers = authenticate(db)
    resp = client.post(URL, json=body(genres=GENRES[:2]), headers=headers)
    assert resp.status_code == 422


def test_rejects_missing_favorite_track(client, db):
    _, headers = authenticate(db)
    payload = body()
    del payload["favorite_track"]
    assert client.post(URL, json=payload, headers=headers).status_code == 422


def test_rejects_repeated_items_padding_the_minimum(client, db):
    _, headers = authenticate(db)
    repeated = [ARTISTS[0], ARTISTS[1], dict(ARTISTS[0], name="Daft Punk (dup)")]
    resp = client.post(URL, json=body(artists=repeated), headers=headers)
    assert resp.status_code == 422


def test_second_call_replaces_previous_preferences(client, db):
    user, headers = authenticate(db)
    client.post(URL, json=body(), headers=headers)

    new_genres = [
        {"deezer_id": 165, "name": "R&B"},
        {"deezer_id": 129, "name": "Jazz"},
        {"deezer_id": 106, "name": "Electro"},
    ]
    resp = client.post(URL, json=body(genres=new_genres), headers=headers)

    assert resp.status_code == 200
    assert [g["name"] for g in resp.json()["genres"]] == ["R&B", "Jazz", "Electro"]
    assert favorite_genre_names(db, user) == {"R&B", "Jazz", "Electro"}
    assert len(favorite_artists(db, user)) == 3


def test_preferences_are_scoped_to_the_authenticated_user(client, db):
    alice, alice_headers = authenticate(db, "alice")
    bob, bob_headers = authenticate(db, "bob")
    client.post(URL, json=body(), headers=alice_headers)

    client.post(URL, json=body(), headers=bob_headers)

    assert len(favorite_genre_names(db, alice)) == 3
    assert len(favorite_genre_names(db, bob)) == 3
    assert len(favorite_artists(db, alice)) == 3
    db.refresh(alice)
    assert alice.onboarding_completed is True


def test_requires_authentication(client, db):
    resp = client.post(URL, json=body())

    assert resp.status_code == 401
    assert db.query(UserFavoriteGenre).count() == 0


def test_rejects_duplicate_beyond_the_minimum(client, db):
    """Three distinct plus a repeat used to slip past validation and 500 on insert."""
    _, headers = authenticate(db)
    with_repeat = [*ARTISTS, dict(ARTISTS[0], name="Daft Punk (dup)")]

    resp = client.post(URL, json=body(artists=with_repeat), headers=headers)

    assert resp.status_code == 422
    assert db.query(UserFavoriteArtist).count() == 0


def test_rejects_oversized_selection(client, db):
    _, headers = authenticate(db)
    too_many = [{"deezer_id": i, "name": f"Genre {i}"} for i in range(1, 60)]
    resp = client.post(URL, json=body(genres=too_many), headers=headers)
    assert resp.status_code == 422


def test_rejects_malformed_items(client, db):
    _, headers = authenticate(db)
    blank = [*ARTISTS[:2], {"deezer_id": 99, "name": ""}]
    non_positive = [*GENRES[:2], {"deezer_id": 0, "name": "Zero"}]

    assert (
        client.post(URL, json=body(artists=blank), headers=headers).status_code == 422
    )
    assert (
        client.post(URL, json=body(genres=non_positive), headers=headers).status_code
        == 422
    )
