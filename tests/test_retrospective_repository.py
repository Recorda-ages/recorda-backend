from datetime import datetime

from app.repositories import retrospective_repository
from tests.factories import add_recorda, add_user


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
