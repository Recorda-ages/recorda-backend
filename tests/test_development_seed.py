from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.development_seed import DEMO_USERNAMES, seed_database
from app.models import (
    AppUser,
    Follow,
    Recorda,
    RecordaComment,
    RecordaLike,
    UserFavoriteArtist,
    UserFavoriteGenre,
)
from tests.factories import add_user


def test_seed_database_creates_ten_complete_demo_users(db: Session) -> None:
    result = seed_database(db)

    users = list(
        db.scalars(select(AppUser).where(AppUser.username.in_(DEMO_USERNAMES)))
    )

    assert result.users_created == 10
    assert len(users) == 10
    assert all(user.profile_picture_url for user in users)
    assert all(user.fav_song_deezer_track_id for user in users)
    assert all(user.fav_song_title for user in users)
    assert all(user.fav_song_artist_name for user in users)
    assert all(user.fav_song_cover_url for user in users)

    for user in users:
        genre_count = len(
            db.scalars(
                select(UserFavoriteGenre).where(
                    UserFavoriteGenre.user_id == user.user_id
                )
            ).all()
        )
        artist_count = len(
            db.scalars(
                select(UserFavoriteArtist).where(
                    UserFavoriteArtist.user_id == user.user_id
                )
            ).all()
        )
        assert genre_count >= 1
        assert artist_count >= 3


def test_seed_database_preserves_the_separate_admin_account(db: Session) -> None:
    result = seed_database(db)

    admin = db.scalar(select(AppUser).where(AppUser.username == "admin"))

    assert result.admin_created == 1
    assert admin is not None
    assert admin.email == "admin@recorda.com"
    assert admin.role == "ADMIN"


def test_seed_database_creates_realistic_recordas(db: Session) -> None:
    result = seed_database(db)

    recordas = list(db.scalars(select(Recorda)))

    assert result.recordas_created == 20
    assert len(recordas) == 20
    assert {recorda.media_type for recorda in recordas} == {"PHOTO", "VIDEO"}
    assert all(recorda.media_url.startswith("https://") for recorda in recordas)
    assert all("exemplo.com" not in recorda.media_url for recorda in recordas)
    assert all(recorda.deezer_track_id for recorda in recordas)
    assert all(recorda.song_title for recorda in recordas)
    assert all(recorda.song_artist_name for recorda in recordas)
    assert all(recorda.song_cover_url.startswith("https://") for recorda in recordas)


def test_seed_database_creates_social_relationships(db: Session) -> None:
    result = seed_database(db)

    follows = list(db.scalars(select(Follow)))
    likes = list(db.scalars(select(RecordaLike)))
    comments = list(db.scalars(select(RecordaComment)))

    assert result.follows_created == 29
    assert result.likes_created == 40
    assert result.comments_created == 20
    assert len(follows) == 29
    assert len(likes) == 40
    assert len(comments) == 20
    assert all(follow.follower_id != follow.following_id for follow in follows)
    assert {follow.status for follow in follows} == {"ACCEPTED", "PENDING"}
    assert all(comment.content.strip() for comment in comments)


def test_seed_database_is_idempotent(db: Session) -> None:
    first_result = seed_database(db)
    second_result = seed_database(db)

    assert first_result.users_created == 10
    assert first_result.admin_created == 1
    assert first_result.recordas_created == 20
    assert first_result.follows_created == 29
    assert first_result.likes_created == 40
    assert first_result.comments_created == 20
    assert second_result.users_created == 0
    assert second_result.admin_created == 0
    assert second_result.recordas_created == 0
    assert second_result.follows_created == 0
    assert second_result.likes_created == 0
    assert second_result.comments_created == 0

    assert len(db.scalars(select(AppUser)).all()) == 11
    assert len(db.scalars(select(Recorda)).all()) == 20
    assert len(db.scalars(select(Follow)).all()) == 29
    assert len(db.scalars(select(RecordaLike)).all()) == 40
    assert len(db.scalars(select(RecordaComment)).all()) == 20


def test_seed_database_enriches_the_existing_legacy_demo_user(db: Session) -> None:
    existing_gabriel = add_user(
        db,
        "gabriel",
        email="gabriel@recorda.com",
        password="User@1234",
    )

    result = seed_database(db)
    seeded_gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))

    assert result.users_created == 9
    assert seeded_gabriel is not None
    assert seeded_gabriel.user_id == existing_gabriel.user_id
    assert seeded_gabriel.profile_picture_url
    assert seeded_gabriel.fav_song_deezer_track_id == "3135556"


def test_seed_database_preserves_an_existing_follow_with_a_different_id(
    db: Session,
) -> None:
    seed_database(db)
    gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    ana = db.scalar(select(AppUser).where(AppUser.username == "ana"))
    assert gabriel is not None
    assert ana is not None

    seeded_follow = db.scalar(
        select(Follow).where(
            Follow.follower_id == gabriel.user_id,
            Follow.following_id == ana.user_id,
        )
    )
    assert seeded_follow is not None
    db.delete(seeded_follow)
    db.commit()
    db.add(
        Follow(
            follower_id=gabriel.user_id,
            following_id=ana.user_id,
            status="ACCEPTED",
        )
    )
    db.commit()

    result = seed_database(db)

    assert result.follows_created == 0
    matching_follows = db.scalars(
        select(Follow).where(
            Follow.follower_id == gabriel.user_id,
            Follow.following_id == ana.user_id,
        )
    ).all()
    assert len(matching_follows) == 1


def test_seeded_demo_user_can_log_in_and_consume_the_feed(
    db: Session, client: TestClient
) -> None:
    seed_database(db)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "gabriel", "password": "User@1234"},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    feed_response = client.get(
        "/api/v1/feed/following?limit=50",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert feed_response.status_code == 200
    items = feed_response.json()["items"]
    assert len(items) == 8
    assert {item["author"]["username"] for item in items} == {
        "ana",
        "lucas",
        "marina",
        "pedro",
    }
    assert "camila" not in {item["author"]["username"] for item in items}
    assert all(item["author"]["profile_picture_url"] for item in items)
