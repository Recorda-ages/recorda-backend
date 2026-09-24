"""Populate development databases with deterministic, realistic data."""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.time import now_utc
from app.db.development_seed_data import (
    COMMENTS,
    FOLLOWS,
    RECORDAS,
    TRACKS,
    USERS,
    UserSeed,
)
from app.db.seed_data import GENRE_SEED
from app.models import (
    AppUser,
    Follow,
    Genre,
    Recorda,
    RecordaComment,
    RecordaLike,
    UserFavoriteArtist,
    UserFavoriteGenre,
)
from app.models.app_user import ROLE_ADMIN, ROLE_USER
from app.models.follow import STATUS_ACCEPTED

DEFAULT_DEMO_PASSWORD = "User@1234"
DEFAULT_ADMIN_PASSWORD = "Admin@1234"
DEMO_USERNAMES = tuple(user.username for user in USERS)
SEED_NAMESPACE = uuid.UUID("8f353bc4-ef23-4e44-97e4-0a02cabf64f6")


@dataclass(frozen=True)
class SeedResult:
    admin_created: int
    users_created: int
    recordas_created: int
    follows_created: int
    likes_created: int
    comments_created: int


def seed_database(
    db: Session,
    *,
    demo_password: str = DEFAULT_DEMO_PASSWORD,
    admin_password: str = DEFAULT_ADMIN_PASSWORD,
) -> SeedResult:
    """Insert missing development fixtures and commit them atomically."""
    try:
        genre_ids = _seed_genres(db)
        admin_created = int(_seed_admin(db, admin_password))
        users_by_username: dict[str, AppUser] = {}
        users_created = 0

        for user_seed in USERS:
            user, was_created = _seed_user(db, user_seed, demo_password)
            users_by_username[user.username] = user
            users_created += int(was_created)
            _seed_preferences(db, user, user_seed, genre_ids)

        recordas_created = _seed_recordas(db, users_by_username)
        recordas_by_key = {
            recorda_seed.key: db.get(
                Recorda,
                uuid.uuid5(SEED_NAMESPACE, f"recorda:{recorda_seed.key}"),
            )
            for recorda_seed in RECORDAS
        }
        follows_created = _seed_follows(db, users_by_username)
        likes_created = _seed_likes(db, users_by_username, recordas_by_key)
        comments_created = _seed_comments(db, users_by_username, recordas_by_key)

        db.commit()
        return SeedResult(
            admin_created=admin_created,
            users_created=users_created,
            recordas_created=recordas_created,
            follows_created=follows_created,
            likes_created=likes_created,
            comments_created=comments_created,
        )
    except Exception:
        db.rollback()
        raise


def _seed_genres(db: Session) -> dict[str, UUID]:
    genre_ids: dict[str, UUID] = {}
    for genre_id, name in GENRE_SEED:
        genre = db.scalar(select(Genre).where(Genre.name == name))
        if genre is None:
            genre = Genre(genre_id=genre_id, name=name)
            db.add(genre)
            db.flush()
        genre_ids[name] = genre.genre_id
    return genre_ids


def _seed_admin(db: Session, password: str) -> bool:
    existing = db.scalar(
        select(AppUser).where(
            or_(
                AppUser.email == "admin@recorda.com",
                AppUser.username == "admin",
            )
        )
    )
    if existing is not None:
        return False

    db.add(
        AppUser(
            username="admin",
            email="admin@recorda.com",
            name="Administrador",
            password_hash=hash_password(password),
            role=ROLE_ADMIN,
        )
    )
    db.flush()
    return True


def _seed_user(
    db: Session, user_seed: UserSeed, demo_password: str
) -> tuple[AppUser, bool]:
    user = db.scalar(
        select(AppUser).where(
            or_(
                AppUser.email == user_seed.email,
                AppUser.username == user_seed.username,
            )
        )
    )
    favorite_track = TRACKS[user_seed.favorite_track]

    if user is None:
        user = AppUser(
            username=user_seed.username,
            email=user_seed.email,
            name=user_seed.name,
            password_hash=hash_password(demo_password),
            profile_picture_url=user_seed.profile_picture_url,
            is_private=user_seed.is_private,
            role=ROLE_USER,
            fav_song_deezer_track_id=favorite_track.deezer_track_id,
            fav_song_title=favorite_track.title,
            fav_song_artist_name=favorite_track.artist_name,
            fav_song_cover_url=favorite_track.cover_url,
            fav_song_preview_url=None,
        )
        db.add(user)
        db.flush()
        return user, True

    if user.profile_picture_url is None:
        user.profile_picture_url = user_seed.profile_picture_url
    if user.fav_song_deezer_track_id is None:
        user.fav_song_deezer_track_id = favorite_track.deezer_track_id
        user.fav_song_title = favorite_track.title
        user.fav_song_artist_name = favorite_track.artist_name
        user.fav_song_cover_url = favorite_track.cover_url
        user.fav_song_preview_url = None
    return user, False


def _seed_preferences(
    db: Session,
    user: AppUser,
    user_seed: UserSeed,
    genre_ids: dict[str, UUID],
) -> None:
    for genre_name in user_seed.genres:
        genre_id = genre_ids[genre_name]
        existing_genre = db.get(UserFavoriteGenre, (user.user_id, genre_id))
        if existing_genre is None:
            db.add(UserFavoriteGenre(user_id=user.user_id, genre_id=genre_id))

    for track_key in user_seed.favorite_artists:
        track = TRACKS[track_key]
        existing_artist = db.get(UserFavoriteArtist, (user.user_id, track.artist_id))
        if existing_artist is None:
            db.add(
                UserFavoriteArtist(
                    user_id=user.user_id,
                    deezer_artist_id=track.artist_id,
                    artist_name=track.artist_name,
                    artist_image_url=track.artist_image_url,
                )
            )


def _seed_recordas(db: Session, users_by_username: dict[str, AppUser]) -> int:
    created = 0
    seed_time = now_utc()
    for recorda_seed in RECORDAS:
        recorda_id = uuid.uuid5(SEED_NAMESPACE, f"recorda:{recorda_seed.key}")
        if db.get(Recorda, recorda_id) is not None:
            continue

        track = TRACKS[recorda_seed.track]
        author = users_by_username[recorda_seed.username]
        db.add(
            Recorda(
                recorda_id=recorda_id,
                user_id=author.user_id,
                media_url=recorda_seed.media_url,
                media_type=recorda_seed.media_type,
                description=recorda_seed.description,
                deezer_track_id=track.deezer_track_id,
                song_title=track.title,
                song_artist_name=track.artist_name,
                song_cover_url=track.cover_url,
                song_preview_url=None,
                created_at=seed_time - timedelta(days=recorda_seed.age_days),
            )
        )
        created += 1
    db.flush()
    return created


def _seed_follows(db: Session, users_by_username: dict[str, AppUser]) -> int:
    created = 0
    seed_time = now_utc()
    for follow_seed in FOLLOWS:
        follower = users_by_username[follow_seed.follower]
        following = users_by_username[follow_seed.following]
        follow_id = uuid.uuid5(
            SEED_NAMESPACE,
            f"follow:{follow_seed.follower}:{follow_seed.following}",
        )
        existing = db.scalar(
            select(Follow).where(
                Follow.follower_id == follower.user_id,
                Follow.following_id == following.user_id,
            )
        )
        if existing is not None:
            continue

        db.add(
            Follow(
                follow_id=follow_id,
                follower_id=follower.user_id,
                following_id=following.user_id,
                status=follow_seed.status,
                requested_at=seed_time - timedelta(days=30),
                accepted_at=(
                    seed_time - timedelta(days=29)
                    if follow_seed.status == STATUS_ACCEPTED
                    else None
                ),
            )
        )
        created += 1
    db.flush()
    return created


def _seed_likes(
    db: Session,
    users_by_username: dict[str, AppUser],
    recordas_by_key: dict[str, Recorda | None],
) -> int:
    created = 0
    recorda_keys = tuple(recorda.key for recorda in RECORDAS)
    seed_time = now_utc()
    for user_index, user_seed in enumerate(USERS):
        user = users_by_username[user_seed.username]
        for offset in (2, 5, 8, 11):
            recorda_key = recorda_keys[(user_index * 2 + offset) % len(recorda_keys)]
            recorda = recordas_by_key[recorda_key]
            if recorda is None:
                raise RuntimeError(f"Recorda de seed ausente: {recorda_key}")
            if db.get(RecordaLike, (user.user_id, recorda.recorda_id)) is not None:
                continue
            db.add(
                RecordaLike(
                    user_id=user.user_id,
                    recorda_id=recorda.recorda_id,
                    created_at=seed_time - timedelta(days=offset),
                )
            )
            created += 1
    db.flush()
    return created


def _seed_comments(
    db: Session,
    users_by_username: dict[str, AppUser],
    recordas_by_key: dict[str, Recorda | None],
) -> int:
    created = 0
    seed_time = now_utc()
    for index, comment_seed in enumerate(COMMENTS):
        comment_id = uuid.uuid5(SEED_NAMESPACE, f"comment:{comment_seed.key}")
        if db.get(RecordaComment, comment_id) is not None:
            continue
        recorda = recordas_by_key[comment_seed.recorda]
        if recorda is None:
            raise RuntimeError(f"Recorda de seed ausente: {comment_seed.recorda}")
        author = users_by_username[comment_seed.username]
        db.add(
            RecordaComment(
                comment_id=comment_id,
                user_id=author.user_id,
                recorda_id=recorda.recorda_id,
                content=comment_seed.content,
                created_at=seed_time - timedelta(hours=index + 1),
            )
        )
        created += 1
    db.flush()
    return created
