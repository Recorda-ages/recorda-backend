import uuid

import pytest

from app.core.time import now_utc
from app.models import Follow
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from app.repositories import follow_repository
from app.services import follow_service
from tests.factories import add_follow, add_user

LIST_ALL = {"q": None, "limit": 100, "offset": 0}


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


@pytest.fixture
def owner_with_mixed_followers(db):
    """Dono com 1 seguidor válido e 3 que não podem contar.

    Cada seguidor inválido quebra uma regra só, para cada filtro ser testado
    isoladamente: status do follow, status da conta e exclusão da conta.
    """
    owner = add_user(db, "owner")
    add_follow(db, add_user(db, "accepted"), owner)
    add_follow(db, add_user(db, "pending"), owner, status=STATUS_PENDING)
    add_follow(db, add_user(db, "suspended", status=STATUS_SUSPENDED), owner)
    add_follow(db, add_user(db, "deleted", deleted_at=now_utc()), owner)
    return owner


@pytest.fixture
def owner_with_mixed_following(db):
    """Dono que segue 1 conta válida e 3 que não podem contar."""
    owner = add_user(db, "owner")
    add_follow(db, owner, add_user(db, "accepted"))
    add_follow(db, owner, add_user(db, "pending"), status=STATUS_PENDING)
    add_follow(db, owner, add_user(db, "suspended", status=STATUS_SUSPENDED))
    add_follow(db, owner, add_user(db, "deleted", deleted_at=now_utc()))
    return owner


def test_count_followers_counts_only_accepted_active_accounts(
    db, owner_with_mixed_followers
):
    assert (
        follow_repository.count_followers(db, owner_with_mixed_followers.user_id) == 1
    )


def test_count_followers_matches_list_followers(db, owner_with_mixed_followers):
    owner_id = owner_with_mixed_followers.user_id

    listed = follow_repository.list_followers(db, owner_id, **LIST_ALL)

    assert follow_repository.count_followers(db, owner_id) == len(listed)


def test_count_following_counts_only_accepted_active_accounts(
    db, owner_with_mixed_following
):
    assert (
        follow_repository.count_following(db, owner_with_mixed_following.user_id) == 1
    )


def test_count_following_matches_list_following(db, owner_with_mixed_following):
    owner_id = owner_with_mixed_following.user_id

    listed = follow_repository.list_following(db, owner_id, **LIST_ALL)

    assert follow_repository.count_following(db, owner_id) == len(listed)


def test_counts_ignore_relationships_of_other_users(db):
    owner = add_user(db, "owner")
    add_follow(db, add_user(db, "alice"), add_user(db, "bob"))

    assert follow_repository.count_followers(db, owner.user_id) == 0
    assert follow_repository.count_following(db, owner.user_id) == 0
