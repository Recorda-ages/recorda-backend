from datetime import UTC, datetime

from app.core.time import local_month_bounds
from app.repositories import retrospective_repository
from tests.factories import add_comment, add_like, add_recorda, add_user


def test_search_retrospectives(db):
    user_id = add_user(db, "Alice")
    different_user_id = add_user(db, "Bob")

    recorda1 = add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 0, 0, 0))
    recorda2 = add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 0, 0, 0))
    add_recorda(db, different_user_id, created_at=datetime(2023, 3, 1, 0, 0, 0))
    add_recorda(
        db,
        user_id,
        created_at=datetime(2023, 4, 1, 0, 0, 0),
        deleted_at=datetime(2023, 5, 1, 0, 0, 0),
    )

    result = retrospective_repository.search_retrospectives(db, user_id.user_id)

    assert set(result) == {recorda1.created_at, recorda2.created_at}


def at(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


NOVEMBER_2026 = local_month_bounds(2026, 11)


def test_count_likes_received_only_for_live_recordas_in_period(db):
    owner = add_user(db, "owner")
    fan1 = add_user(db, "fan1")
    fan2 = add_user(db, "fan2")
    in_period = add_recorda(db, owner, created_at=at(2026, 11, 10, 15))
    before = add_recorda(db, owner, created_at=at(2026, 11, 1, 2, 59))  # 31/10 local
    deleted = add_recorda(
        db, owner, created_at=at(2026, 11, 12, 15), deleted_at=at(2026, 11, 13)
    )
    foreign = add_recorda(db, fan1, created_at=at(2026, 11, 10, 15))
    add_like(db, fan1, in_period)
    add_like(db, fan2, in_period)
    add_like(db, fan1, before)
    add_like(db, fan1, deleted)
    add_like(db, owner, foreign)

    total = retrospective_repository.count_likes_received(
        db, owner.user_id, *NOVEMBER_2026
    )

    assert total == 2


def test_count_comments_received_ignores_deleted_comments(db):
    owner = add_user(db, "owner")
    fan = add_user(db, "fan")
    in_period = add_recorda(db, owner, created_at=at(2026, 11, 10, 15))
    after = add_recorda(db, owner, created_at=at(2026, 12, 1, 3))  # 01/12 local
    add_comment(db, fan, in_period)
    add_comment(db, owner, in_period)
    add_comment(db, fan, in_period, deleted_at=at(2026, 11, 11))
    add_comment(db, fan, after)

    total = retrospective_repository.count_comments_received(
        db, owner.user_id, *NOVEMBER_2026
    )

    assert total == 2


def test_counts_are_zero_without_recordas_in_period(db):
    owner = add_user(db, "owner")

    assert (
        retrospective_repository.count_likes_received(db, owner.user_id, *NOVEMBER_2026)
        == 0
    )
    assert (
        retrospective_repository.count_comments_received(
            db, owner.user_id, *NOVEMBER_2026
        )
        == 0
    )
