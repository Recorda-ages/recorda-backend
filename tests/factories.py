import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core import security
from app.core.time import now_utc
from app.db.seed_data import GENRE_NAMESPACE
from app.models import (
    AppUser,
    Follow,
    Notification,
    Recorda,
    UserFavoriteArtist,
    UserFavoriteGenre,
)
from app.models.app_user import ROLE_USER
from app.models.follow import STATUS_ACCEPTED


def add_user(
    db: Session,
    username: str,
    *,
    password: str | None = None,
    role: str = ROLE_USER,
    **fields,
) -> AppUser:
    user = AppUser(
        name=fields.pop("name", username.title()),
        email=fields.pop("email", f"{username}@example.com"),
        username=username,
        password_hash=security.hash_password(password) if password else None,
        role=role,
        **fields,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_recorda(db: Session, author: AppUser, **fields) -> Recorda:
    values = {
        "media_url": "/api/v1/recordas/media/abc.jpg",
        "media_type": "PHOTO",
        "deezer_track_id": "3135556",
        "song_title": "Song of Silence",
        "song_artist_name": "Disturbed",
        "song_cover_url": "https://e.deezer.com/cover.jpg",
        "description": "By Disturbed",
    }
    values.update(fields)
    recorda = Recorda(user_id=author.user_id, **values)
    db.add(recorda)
    db.commit()
    db.refresh(recorda)
    return recorda


def add_follow(
    db: Session,
    follower: AppUser,
    following: AppUser,
    *,
    status: str = STATUS_ACCEPTED,
) -> Follow:
    follow = Follow(
        follower_id=follower.user_id,
        following_id=following.user_id,
        status=status,
        accepted_at=now_utc() if status == STATUS_ACCEPTED else None,
    )
    db.add(follow)
    db.commit()
    db.refresh(follow)
    return follow


def add_notification(
    db: Session, recipient: AppUser, type_: str, **fields
) -> Notification:
    sender = fields.pop("sender", None)
    notification = Notification(
        recipient_id=recipient.user_id,
        sender_id=sender.user_id if sender else None,
        type=type_,
        **fields,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def add_favorite_genres(db: Session, user: AppUser, *genre_names: str) -> None:
    """Marca gêneros do seed como favoritos do usuário, pelo nome."""
    db.add_all(
        UserFavoriteGenre(
            user_id=user.user_id,
            genre_id=uuid.uuid5(GENRE_NAMESPACE, name),
        )
        for name in genre_names
    )
    db.commit()


def add_favorite_artists(db: Session, user: AppUser, *artist_names: str) -> None:
    """Marca artistas como favoritos, usando o nome também como id do Deezer."""
    db.add_all(
        UserFavoriteArtist(
            user_id=user.user_id,
            deezer_artist_id=name,
            artist_name=name,
        )
        for name in artist_names
    )
    db.commit()


def token_for(user: AppUser, expires_delta: timedelta | None = None) -> str:
    return security.create_access_token(
        subject=str(user.user_id),
        additional_claims={"username": user.username, "role": user.role},
        expires_delta=expires_delta,
    )


def auth_headers(user: AppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}
