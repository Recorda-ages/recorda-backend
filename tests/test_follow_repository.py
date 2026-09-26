import uuid

from app.models import Follow
from app.repositories import follow_repository
from app.services import follow_service
from tests.factories import add_user


def test_delete_follow_by_follow_id(db):
    follower = add_user(db, "follower")
    following = add_user(db, "following")
    follow = Follow(
        follower_id=follower.user_id,
        following_id=following.user_id,
        status="ACCEPTED",
    )
    db.add(follow)
    db.commit()

    assert follow_service.delete_follow(db, follow.follow_id) is True
    assert follow_repository.get_by_id(db, follow.follow_id) is None


def test_delete_follow_returns_false_when_id_does_not_exist(db):
    assert follow_service.delete_follow(db, uuid.uuid4()) is False
