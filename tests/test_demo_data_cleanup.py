from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.demo_data_cleanup import remove_demo_data
from app.db.development_seed import DEMO_USERNAMES, seed_database
from app.models import AppUser, Follow, Recorda, RecordaComment, RecordaLike
from app.models.app_user import STATUS_SUSPENDED
from tests.factories import (
    add_comment,
    add_follow,
    add_like,
    add_moderation_action,
    add_recorda,
    add_user,
)


def test_remove_demo_data_deletes_seed_users_and_their_content(db: Session) -> None:
    seed_database(db)
    real_user = add_user(db, "real")
    real_recorda = add_recorda(db, real_user)
    demo_user = db.scalar(select(AppUser).where(AppUser.username == "gabriel"))
    demo_recorda = db.scalar(
        select(Recorda).where(Recorda.user_id == demo_user.user_id)
    )
    add_like(db, real_user, demo_recorda)
    add_comment(db, real_user, demo_recorda)
    add_like(db, demo_user, real_recorda)
    add_follow(db, real_user, demo_user)

    result = remove_demo_data(db)

    remaining_usernames = set(db.scalars(select(AppUser.username)))
    assert remaining_usernames == {"real"}
    assert result.users_deleted == len(DEMO_USERNAMES) + 1
    assert list(db.scalars(select(Recorda.recorda_id))) == [real_recorda.recorda_id]
    assert db.scalars(select(RecordaLike)).all() == []
    assert db.scalars(select(RecordaComment)).all() == []
    assert db.scalars(select(Follow)).all() == []


def test_remove_demo_data_deactivates_users_kept_by_the_audit_log(db: Session) -> None:
    seed_database(db)
    real_user = add_user(db, "real")
    demo_admin = db.scalar(select(AppUser).where(AppUser.username == "admin"))
    add_moderation_action(db, demo_admin, target_user=real_user)

    result = remove_demo_data(db)

    db.refresh(demo_admin)
    assert result.users_deactivated == 1
    assert demo_admin.deleted_at is not None
    assert demo_admin.status == STATUS_SUSPENDED
    assert demo_admin.password_hash is None
    assert db.get(AppUser, real_user.user_id) is not None


def test_remove_demo_data_keeps_real_accounts_sharing_a_demo_username(
    db: Session,
) -> None:
    add_user(db, "ana", email="ana.real@example.com")

    result = remove_demo_data(db)

    assert result.users_deleted == 0
    assert db.scalar(select(AppUser).where(AppUser.username == "ana")) is not None
