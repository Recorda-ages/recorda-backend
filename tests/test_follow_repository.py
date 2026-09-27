import uuid

from app.models import Follow
from app.repositories import follow_repository
from app.services import follow_service
from tests.factories import add_user


def test_delete_follow_by_follower_and_target(db):
    follower = add_user(db, "follower")
    following = add_user(db, "following")
    follow = Follow(
        follower_id=follower.user_id,
        following_id=following.user_id,
        status="ACCEPTED",
    )
    db.add(follow)
    db.commit()

    assert follow_service.delete_follow(db, following.user_id, follower) is True
    assert (
        follow_repository.get_by_users(db, follower.user_id, following.user_id) is None
    )


def test_delete_follow_returns_false_when_relationship_does_not_exist(db):
    follower = add_user(db, "follower")
    assert follow_service.delete_follow(db, uuid.uuid4(), follower) is False
