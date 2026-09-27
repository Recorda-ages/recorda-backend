import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db import development_seed
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
from app.models.app_user import ROLE_ADMIN, ROLE_USER, STATUS_ACTIVE, STATUS_SUSPENDED
from scripts import seed as seed_script
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
    first_follow_timestamps = {
        (follow.follower_id, follow.following_id): (
            follow.requested_at,
            follow.accepted_at,
        )
        for follow in db.scalars(select(Follow))
    }
    second_result = seed_database(db)
    second_follow_timestamps = {
        (follow.follower_id, follow.following_id): (
            follow.requested_at,
            follow.accepted_at,
        )
        for follow in db.scalars(select(Follow))
    }

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
    assert second_follow_timestamps == first_follow_timestamps


def test_seed_database_creates_a_causally_valid_timeline(db: Session) -> None:
    seed_database(db)

    users_by_id = {user.user_id: user for user in db.scalars(select(AppUser))}
    recordas_by_id = {
        recorda.recorda_id: recorda for recorda in db.scalars(select(Recorda))
    }
    follows = list(db.scalars(select(Follow)))
    last_follow_event = max(
        follow.accepted_at or follow.requested_at for follow in follows
    )

    for recorda in recordas_by_id.values():
        assert recorda.created_at >= users_by_id[recorda.user_id].created_at
        assert recorda.created_at >= last_follow_event

    for follow in follows:
        assert follow.requested_at >= users_by_id[follow.follower_id].created_at
        assert follow.requested_at >= users_by_id[follow.following_id].created_at
        if follow.accepted_at is not None:
            assert follow.accepted_at >= follow.requested_at

    for like in db.scalars(select(RecordaLike)):
        assert like.created_at >= users_by_id[like.user_id].created_at
        assert like.created_at >= recordas_by_id[like.recorda_id].created_at

    for comment in db.scalars(select(RecordaComment)):
        assert comment.created_at >= users_by_id[comment.user_id].created_at
        assert comment.created_at >= recordas_by_id[comment.recorda_id].created_at


def test_seed_database_reconciles_configured_passwords_and_admin_state(
    db: Session,
) -> None:
    seed_database(
        db,
        demo_password="primeira-senha-demo",
        admin_password="primeira-senha-admin",
    )
    admin = db.scalar(select(AppUser).where(AppUser.username == "admin"))
    gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    assert admin is not None
    assert gabriel is not None
    admin.status = STATUS_SUSPENDED
    admin.role = ROLE_USER
    db.commit()

    seed_database(
        db,
        demo_password="segunda-senha-demo",
        admin_password="segunda-senha-admin",
    )
    db.refresh(admin)
    db.refresh(gabriel)

    assert verify_password("segunda-senha-demo", gabriel.password_hash)
    assert not verify_password("primeira-senha-demo", gabriel.password_hash)
    assert verify_password("segunda-senha-admin", admin.password_hash)
    assert not verify_password("primeira-senha-admin", admin.password_hash)
    assert admin.status == STATUS_ACTIVE
    assert admin.role == ROLE_ADMIN


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


def test_seed_database_repairs_a_partial_favorite_track(db: Session) -> None:
    existing_gabriel = add_user(
        db,
        "gabriel",
        email="gabriel@recorda.com",
        password="User@1234",
    )
    existing_gabriel.fav_song_deezer_track_id = "3135556"
    existing_gabriel.fav_song_title = None
    existing_gabriel.fav_song_artist_name = None
    existing_gabriel.fav_song_cover_url = None
    db.commit()

    seed_database(db)
    db.refresh(existing_gabriel)

    assert existing_gabriel.fav_song_title == "Harder, Better, Faster, Stronger"
    assert existing_gabriel.fav_song_artist_name == "Daft Punk"
    assert existing_gabriel.fav_song_cover_url


def test_seed_database_rejects_split_email_and_username_identity(db: Session) -> None:
    add_user(db, "gabriel", email="other@recorda.com")
    add_user(db, "other", email="gabriel@recorda.com")

    with pytest.raises(RuntimeError, match="email e username"):
        seed_database(db)


@pytest.mark.parametrize(
    ("username", "email"),
    [
        ("other", "gabriel@recorda.com"),
        ("gabriel", "other@recorda.com"),
    ],
)
def test_seed_database_rejects_a_partial_fixture_identity(
    db: Session,
    username: str,
    email: str,
) -> None:
    add_user(db, username, email=email)

    with pytest.raises(RuntimeError, match="não identificam a mesma conta"):
        seed_database(db)


def test_seed_database_soft_deletes_known_legacy_recordas(db: Session) -> None:
    legacy_user = add_user(
        db,
        "gabriel",
        email="gabriel@recorda.com",
        password="User@1234",
    )
    legacy_recorda = Recorda(
        user_id=legacy_user.user_id,
        media_url="https://exemplo.com/fotos/praia.jpg",
        media_type="PHOTO",
        description="Dia incrível na praia com os amigos.",
        deezer_track_id="3135556",
        song_title="Harder, Better, Faster, Stronger",
        song_artist_name="Daft Punk",
        song_cover_url="https://exemplo.com/covers/daftpunk.jpg",
    )
    db.add(legacy_recorda)
    db.commit()

    seed_database(db)
    db.refresh(legacy_recorda)

    assert legacy_recorda.deleted_at is not None
    live_recordas = db.scalars(
        select(Recorda).where(Recorda.deleted_at.is_(None))
    ).all()
    assert len(live_recordas) == 20
    assert all("exemplo.com" not in recorda.media_url for recorda in live_recordas)


def test_seed_database_preserves_non_fixture_recorda_using_a_legacy_url(
    db: Session,
) -> None:
    legacy_user = add_user(
        db,
        "gabriel",
        email="gabriel@recorda.com",
        password="User@1234",
    )
    legitimate_recorda = Recorda(
        user_id=legacy_user.user_id,
        media_url="https://exemplo.com/fotos/praia.jpg",
        media_type="PHOTO",
        description="Conteúdo local que não pertence ao seed antigo",
        deezer_track_id="3135556",
        song_title="Harder, Better, Faster, Stronger",
        song_artist_name="Daft Punk",
        song_cover_url="https://exemplo.com/covers/daftpunk.jpg",
    )
    db.add(legitimate_recorda)
    db.commit()

    seed_database(db)
    db.refresh(legitimate_recorda)

    assert legitimate_recorda.deleted_at is None


def test_seed_database_restores_a_soft_deleted_demo_user(db: Session) -> None:
    seed_database(db)
    gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    assert gabriel is not None
    gabriel.deleted_at = gabriel.created_at
    db.commit()

    result = seed_database(db)
    db.refresh(gabriel)

    assert result.users_created == 0
    assert gabriel.deleted_at is None


def test_seed_database_restores_a_soft_deleted_seed_recorda(db: Session) -> None:
    seed_database(db)
    recorda = db.scalar(
        select(Recorda).where(
            Recorda.description == "Uma trilha, uma vista incrível e a música certa."
        )
    )
    assert recorda is not None
    recorda.deleted_at = recorda.created_at
    db.commit()

    result = seed_database(db)
    db.refresh(recorda)

    assert result.recordas_created == 0
    assert recorda.deleted_at is None


def test_seed_database_restores_a_soft_deleted_seed_comment(db: Session) -> None:
    seed_database(db)
    comment = db.scalar(
        select(RecordaComment).where(RecordaComment.content == "Que vista linda!")
    )
    assert comment is not None
    comment.deleted_at = comment.created_at
    db.commit()

    result = seed_database(db)
    db.refresh(comment)

    assert result.comments_created == 0
    assert comment.deleted_at is None


def test_seed_database_rolls_back_all_changes_on_failure(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_while_seeding_recordas(*_args, **_kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(development_seed, "_seed_recordas", fail_while_seeding_recordas)

    with pytest.raises(RuntimeError, match="falha simulada"):
        seed_database(db)

    demo_users = db.scalars(
        select(AppUser).where(AppUser.username.in_(DEMO_USERNAMES))
    ).all()
    assert demo_users == []


def test_seed_cli_rejects_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(seed_script.settings, "environment", "production")

    with pytest.raises(RuntimeError, match="não pode rodar em produção"):
        seed_script.seed()


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


@pytest.mark.parametrize(
    ("following_username", "wrong_status", "expected_status"),
    [
        ("ana", "PENDING", "ACCEPTED"),
        ("camila", "ACCEPTED", "PENDING"),
    ],
)
def test_seed_database_restores_the_expected_follow_status(
    db: Session,
    following_username: str,
    wrong_status: str,
    expected_status: str,
) -> None:
    seed_database(db)
    gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    following = db.scalar(select(AppUser).where(AppUser.username == following_username))
    assert gabriel is not None
    assert following is not None
    follow = db.scalar(
        select(Follow).where(
            Follow.follower_id == gabriel.user_id,
            Follow.following_id == following.user_id,
        )
    )
    assert follow is not None
    follow.status = wrong_status
    follow.accepted_at = follow.requested_at if wrong_status == "ACCEPTED" else None
    db.commit()

    result = seed_database(db)
    db.refresh(follow)

    assert result.follows_created == 0
    assert follow.status == expected_status
    if expected_status == "ACCEPTED":
        assert follow.accepted_at is not None
        assert follow.accepted_at >= follow.requested_at
    else:
        assert follow.accepted_at is None


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


def test_seeded_demo_user_can_consume_the_profile(
    db: Session, client: TestClient
) -> None:
    seed_database(db)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "gabriel", "password": "User@1234"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    profile = response.json()
    assert profile["username"] == "gabriel"
    assert profile["profile_picture_url"]
    assert profile["favorite_song"]["deezer_track_id"] == "3135556"
    assert len(profile["favorite_genres"]) == 3
    assert len(profile["favorite_artists"]) == 3
    assert len(profile["recordas"]) == 2


def test_seed_restores_a_suspended_demo_user_and_its_access(
    db: Session,
    client: TestClient,
) -> None:
    seed_database(db)
    gabriel = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    assert gabriel is not None
    gabriel.status = STATUS_SUSPENDED
    gabriel.role = ROLE_ADMIN
    db.commit()

    blocked_login = client.post(
        "/api/v1/auth/login",
        json={"username": "gabriel", "password": "User@1234"},
    )
    assert blocked_login.status_code == 401

    seed_database(db)
    db.refresh(gabriel)

    assert gabriel.status == STATUS_ACTIVE
    assert gabriel.role == ROLE_USER
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "gabriel", "password": "User@1234"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/feed/following", headers=headers).status_code == 200
    assert client.get("/api/v1/users/me/profile", headers=headers).status_code == 200
