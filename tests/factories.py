from datetime import timedelta

from sqlalchemy.orm import Session

from app.core import security
from app.core.time import now_utc
from app.models import AppUser, Follow, Recorda
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


def token_for(user: AppUser, expires_delta: timedelta | None = None) -> str:
    return security.create_access_token(
        subject=str(user.user_id),
        additional_claims={"username": user.username, "role": user.role},
        expires_delta=expires_delta,
    )


def auth_headers(user: AppUser) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}
