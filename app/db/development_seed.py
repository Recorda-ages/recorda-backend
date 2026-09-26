"""Populate development databases with deterministic, realistic data."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
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
from app.models.app_user import ROLE_ADMIN, ROLE_USER, STATUS_ACTIVE
from app.models.follow import STATUS_ACCEPTED

DEFAULT_DEMO_PASSWORD = "User@1234"
DEFAULT_ADMIN_PASSWORD = "Admin@1234"
DEMO_USERNAMES = tuple(user.username for user in USERS)
SEED_NAMESPACE = uuid.UUID("8f353bc4-ef23-4e44-97e4-0a02cabf64f6")
SEED_REFERENCE_TIME = datetime(2026, 2, 15, 12, tzinfo=UTC)
SEED_USER_CREATED_AT = datetime(2026, 1, 1, 12, tzinfo=UTC)
SEED_FOLLOW_REQUESTED_AT = datetime(2026, 1, 15, 12, tzinfo=UTC)
SEED_FOLLOW_ACCEPTED_AT = datetime(2026, 1, 16, 12, tzinfo=UTC)


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
        _retire_legacy_recordas(db)
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
    existing = _find_seed_user(
        db,
        email="admin@recorda.com",
        username="admin",
    )
    if existing is not None:
        existing.deleted_at = None
        existing.status = STATUS_ACTIVE
        existing.role = ROLE_ADMIN
        _set_timestamp(existing, "created_at", SEED_USER_CREATED_AT)
        _reconcile_password(existing, password)
        return False

    db.add(
        AppUser(
            username="admin",
            email="admin@recorda.com",
            name="Administrador",
            password_hash=hash_password(password),
            role=ROLE_ADMIN,
            status=STATUS_ACTIVE,
            created_at=SEED_USER_CREATED_AT,
        )
    )
    db.flush()
    return True


def _seed_user(
    db: Session, user_seed: UserSeed, demo_password: str
) -> tuple[AppUser, bool]:
    user = _find_seed_user(
        db,
        email=user_seed.email,
        username=user_seed.username,
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
            status=STATUS_ACTIVE,
            fav_song_deezer_track_id=favorite_track.deezer_track_id,
            fav_song_title=favorite_track.title,
            fav_song_artist_name=favorite_track.artist_name,
            fav_song_cover_url=favorite_track.cover_url,
            fav_song_preview_url=None,
            created_at=SEED_USER_CREATED_AT,
        )
        db.add(user)
        db.flush()
        return user, True

    if user.profile_picture_url is None:
        user.profile_picture_url = user_seed.profile_picture_url
    user.deleted_at = None
    user.status = STATUS_ACTIVE
    user.role = ROLE_USER
    _set_timestamp(user, "created_at", SEED_USER_CREATED_AT)
    _reconcile_password(user, demo_password)
    favorite_fields = {
        "fav_song_deezer_track_id": favorite_track.deezer_track_id,
        "fav_song_title": favorite_track.title,
        "fav_song_artist_name": favorite_track.artist_name,
        "fav_song_cover_url": favorite_track.cover_url,
    }
    for field_name, value in favorite_fields.items():
        if getattr(user, field_name) is None:
            setattr(user, field_name, value)
    return user, False


def _reconcile_password(user: AppUser, password: str) -> None:
    """Keep a fixture password aligned without rehashing on every seed run."""
    if not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)


def _set_timestamp(entity: object, field_name: str, expected: datetime | None) -> None:
    """Set a canonical UTC timestamp only when its stored value differs."""
    current = getattr(entity, field_name)
    if current is None or expected is None:
        if current != expected:
            setattr(entity, field_name, expected)
        return

    if _as_utc(current) != _as_utc(expected):
        setattr(entity, field_name, expected)


def _as_utc(value: datetime) -> datetime:
    """Treat naive database timestamps as UTC and normalize aware values."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _find_seed_user(
    db: Session,
    *,
    email: str,
    username: str,
) -> AppUser | None:
    """Resolve a fixture identity without merging two different accounts."""
    user_by_email = db.scalar(select(AppUser).where(AppUser.email == email))
    user_by_username = db.scalar(select(AppUser).where(AppUser.username == username))
    if user_by_email is None and user_by_username is None:
        return None
    if (
        user_by_email is None
        or user_by_username is None
        or user_by_email.user_id != user_by_username.user_id
    ):
        raise RuntimeError(
            "Conflito no seed: email e username não identificam a mesma conta "
            f"({email}, {username})."
        )
    return user_by_email


def _retire_legacy_recordas(db: Session) -> None:
    """Hide only the known fake fixtures created by the previous seed."""
    legacy_fixtures = (
        (
            "https://exemplo.com/fotos/praia.jpg",
            "Dia incrível na praia com os amigos.",
            "3135556",
            "Harder, Better, Faster, Stronger",
            "Daft Punk",
            "https://exemplo.com/covers/daftpunk.jpg",
        ),
        (
            "https://exemplo.com/fotos/formatura.jpg",
            "Formatura — fim de uma era.",
            "908460",
            "Good Riddance (Time of Your Life)",
            "Green Day",
            "https://exemplo.com/covers/greenday.jpg",
        ),
    )
    legacy_recordas = db.scalars(
        select(Recorda)
        .join(AppUser, AppUser.user_id == Recorda.user_id)
        .where(
            AppUser.username == "gabriel",
            AppUser.email == "gabriel@recorda.com",
            Recorda.deleted_at.is_(None),
            or_(
                *(
                    and_(
                        Recorda.media_url == media_url,
                        Recorda.description == description,
                        Recorda.deezer_track_id == track_id,
                        Recorda.song_title == title,
                        Recorda.song_artist_name == artist,
                        Recorda.song_cover_url == cover_url,
                    )
                    for media_url, description, track_id, title, artist, cover_url in legacy_fixtures
                )
            ),
        )
    )
    retired_at = now_utc()
    for recorda in legacy_recordas:
        recorda.deleted_at = retired_at


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
    for recorda_seed in RECORDAS:
        recorda_id = uuid.uuid5(SEED_NAMESPACE, f"recorda:{recorda_seed.key}")
        created_at = SEED_REFERENCE_TIME - timedelta(days=recorda_seed.age_days)
        existing = db.get(Recorda, recorda_id)
        if existing is not None:
            existing.deleted_at = None
            _set_timestamp(existing, "created_at", created_at)
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
                created_at=created_at,
            )
        )
        created += 1
    db.flush()
    return created


def _seed_follows(db: Session, users_by_username: dict[str, AppUser]) -> int:
    created = 0
    for follow_seed in FOLLOWS:
        follower = users_by_username[follow_seed.follower]
        following = users_by_username[follow_seed.following]
        accepted_at = (
            SEED_FOLLOW_ACCEPTED_AT if follow_seed.status == STATUS_ACCEPTED else None
        )
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
            existing.status = follow_seed.status
            _set_timestamp(existing, "requested_at", SEED_FOLLOW_REQUESTED_AT)
            _set_timestamp(existing, "accepted_at", accepted_at)
            continue

        db.add(
            Follow(
                follow_id=follow_id,
                follower_id=follower.user_id,
                following_id=following.user_id,
                status=follow_seed.status,
                requested_at=SEED_FOLLOW_REQUESTED_AT,
                accepted_at=accepted_at,
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
    for user_index, user_seed in enumerate(USERS):
        user = users_by_username[user_seed.username]
        for interaction_index, offset in enumerate((2, 5, 8, 11)):
            recorda_key = recorda_keys[(user_index * 2 + offset) % len(recorda_keys)]
            recorda = recordas_by_key[recorda_key]
            if recorda is None:
                raise RuntimeError(f"Recorda de seed ausente: {recorda_key}")
            created_at = recorda.created_at + timedelta(
                hours=interaction_index + 1,
                minutes=user_index,
            )
            existing = db.get(RecordaLike, (user.user_id, recorda.recorda_id))
            if existing is not None:
                _set_timestamp(existing, "created_at", created_at)
                continue
            db.add(
                RecordaLike(
                    user_id=user.user_id,
                    recorda_id=recorda.recorda_id,
                    created_at=created_at,
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
    for index, comment_seed in enumerate(COMMENTS):
        comment_id = uuid.uuid5(SEED_NAMESPACE, f"comment:{comment_seed.key}")
        recorda = recordas_by_key[comment_seed.recorda]
        if recorda is None:
            raise RuntimeError(f"Recorda de seed ausente: {comment_seed.recorda}")
        created_at = recorda.created_at + timedelta(
            hours=12,
            minutes=index,
        )
        existing = db.get(RecordaComment, comment_id)
        if existing is not None:
            existing.deleted_at = None
            _set_timestamp(existing, "created_at", created_at)
            continue
        author = users_by_username[comment_seed.username]
        db.add(
            RecordaComment(
                comment_id=comment_id,
                user_id=author.user_id,
                recorda_id=recorda.recorda_id,
                content=comment_seed.content,
                created_at=created_at,
            )
        )
        created += 1
    db.flush()
    return created
