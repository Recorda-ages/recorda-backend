from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser, Follow
from app.repositories import follow_repository, user_repository


class FollowTargetNotFoundError(Exception):
    pass


class SelfFollowError(Exception):
    pass


class DuplicateFollowError(Exception):
    pass


def create_follow(db: Session, user_id: UUID, current_user: AppUser) -> str:
    if current_user.user_id == user_id:
        raise SelfFollowError

    target_user = user_repository.get_by_id(db, user_id)
    if target_user is None:
        raise FollowTargetNotFoundError
    if follow_repository.get_by_users(db, current_user.user_id, user_id) is not None:
        raise DuplicateFollowError

    requested_at = now_utc()
    is_private = target_user.is_private
    follow = Follow(
        follower_id=current_user.user_id,
        following_id=user_id,
        status="PENDING" if is_private else "ACCEPTED",
        requested_at=requested_at,
        accepted_at=None if is_private else requested_at,
    )
    follow_repository.create(db, follow)
    return "solicitado" if is_private else "seguindo"


def delete_follow(db: Session, user_id: UUID, current_user: AppUser) -> bool:
    follow = follow_repository.get_by_users(db, current_user.user_id, user_id)
    if follow is None:
        return False
    follow_repository.delete(db, follow)
    return True
