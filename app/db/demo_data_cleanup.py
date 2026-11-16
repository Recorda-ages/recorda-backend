from dataclasses import dataclass

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.db.development_seed_data import USERS
from app.models import (
    AppUser,
    Follow,
    ModerationAction,
    Notification,
    Recorda,
    RecordaComment,
    RecordaLike,
    RecordaMention,
    Report,
    UserFavoriteArtist,
    UserFavoriteGenre,
)
from app.models.app_user import STATUS_SUSPENDED

DEMO_IDENTITIES = (("admin", "admin@recorda.com"),) + tuple(
    (user.username, user.email) for user in USERS
)


@dataclass(frozen=True)
class CleanupResult:
    users_deleted: int
    users_deactivated: int
    recordas_deleted: int


def find_demo_users(db: Session) -> list[AppUser]:
    usernames = [username.lower() for username, _ in DEMO_IDENTITIES]
    emails = [email.lower() for _, email in DEMO_IDENTITIES]
    return list(
        db.scalars(
            select(AppUser).where(
                func.lower(AppUser.username).in_(usernames),
                func.lower(AppUser.email).in_(emails),
            )
        )
    )


def remove_demo_data(db: Session) -> CleanupResult:
    users = find_demo_users(db)
    user_ids = [user.user_id for user in users]
    if not user_ids:
        return CleanupResult(0, 0, 0)

    recorda_ids = list(
        db.scalars(select(Recorda.recorda_id).where(Recorda.user_id.in_(user_ids)))
    )
    comment_ids = list(
        db.scalars(
            select(RecordaComment.comment_id).where(
                or_(
                    RecordaComment.user_id.in_(user_ids),
                    RecordaComment.recorda_id.in_(recorda_ids),
                )
            )
        )
    )
    audited_ids = set(
        db.scalars(
            select(ModerationAction.admin_id).where(
                ModerationAction.admin_id.in_(user_ids)
            )
        )
    ) | set(
        db.scalars(
            select(ModerationAction.target_user_id).where(
                ModerationAction.target_user_id.in_(user_ids)
            )
        )
    )

    db.execute(
        delete(Notification).where(
            or_(
                Notification.recipient_id.in_(user_ids),
                Notification.sender_id.in_(user_ids),
                Notification.recorda_id.in_(recorda_ids),
                Notification.comment_id.in_(comment_ids),
            )
        )
    )
    db.execute(
        delete(Report).where(
            or_(
                Report.reporter_id.in_(user_ids),
                Report.reported_user_id.in_(user_ids),
                Report.recorda_id.in_(recorda_ids),
                Report.comment_id.in_(comment_ids),
            )
        )
    )
    db.execute(
        delete(RecordaMention).where(
            or_(
                RecordaMention.user_id.in_(user_ids),
                RecordaMention.recorda_id.in_(recorda_ids),
            )
        )
    )
    db.execute(delete(RecordaComment).where(RecordaComment.comment_id.in_(comment_ids)))
    db.execute(
        delete(RecordaLike).where(
            or_(
                RecordaLike.user_id.in_(user_ids),
                RecordaLike.recorda_id.in_(recorda_ids),
            )
        )
    )
    db.execute(
        delete(Follow).where(
            or_(Follow.follower_id.in_(user_ids), Follow.following_id.in_(user_ids))
        )
    )
    db.execute(delete(UserFavoriteGenre).where(UserFavoriteGenre.user_id.in_(user_ids)))
    db.execute(
        delete(UserFavoriteArtist).where(UserFavoriteArtist.user_id.in_(user_ids))
    )
    db.execute(delete(Recorda).where(Recorda.recorda_id.in_(recorda_ids)))

    deletable_ids = [user_id for user_id in user_ids if user_id not in audited_ids]
    db.execute(delete(AppUser).where(AppUser.user_id.in_(deletable_ids)))

    deactivated_at = now_utc()
    for user in users:
        if user.user_id in audited_ids:
            user.deleted_at = deactivated_at
            user.status = STATUS_SUSPENDED
            user.password_hash = None

    db.commit()
    return CleanupResult(
        users_deleted=len(deletable_ids),
        users_deactivated=len(audited_ids),
        recordas_deleted=len(recorda_ids),
    )
