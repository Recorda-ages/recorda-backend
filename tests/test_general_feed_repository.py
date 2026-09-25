"""Testes de integração do app/repositories/general_feed_repository.py."""

from datetime import UTC, datetime

from app.core.time import now_utc
from app.models import RecordaLike
from app.models.app_user import STATUS_SUSPENDED
from app.models.follow import STATUS_PENDING
from app.repositories.feed_repository import apply_cursor
from app.repositories.general_feed_repository import (
    get_candidate_author_ids,
    get_general_feed_query,
)
from tests.factories import add_follow, add_recorda, add_user


class TestGetCandidateAuthorIds:
    def test_includes_public_account(self, db):
        viewer = add_user(db, "viewer")
        public_author = add_user(db, "publico")

        assert public_author.user_id in get_candidate_author_ids(db, viewer.user_id)

    def test_excludes_private_account_not_followed(self, db):
        viewer = add_user(db, "viewer")
        private_author = add_user(db, "privado", is_private=True)

        assert private_author.user_id not in get_candidate_author_ids(
            db, viewer.user_id
        )

    def test_excludes_private_account_with_pending_follow(self, db):
        viewer = add_user(db, "viewer")
        private_author = add_user(db, "privado", is_private=True)
        add_follow(db, viewer, private_author, status=STATUS_PENDING)

        assert private_author.user_id not in get_candidate_author_ids(
            db, viewer.user_id
        )

    def test_includes_private_account_with_accepted_follow(self, db):
        viewer = add_user(db, "viewer")
        private_author = add_user(db, "privado", is_private=True)
        add_follow(db, viewer, private_author)

        assert private_author.user_id in get_candidate_author_ids(db, viewer.user_id)

    def test_excludes_the_current_user(self, db):
        viewer = add_user(db, "viewer")

        assert viewer.user_id not in get_candidate_author_ids(db, viewer.user_id)

    def test_excludes_suspended_account(self, db):
        viewer = add_user(db, "viewer")
        suspended = add_user(db, "suspenso", status=STATUS_SUSPENDED)

        assert suspended.user_id not in get_candidate_author_ids(db, viewer.user_id)

    def test_excludes_soft_deleted_account(self, db):
        viewer = add_user(db, "viewer")
        deleted = add_user(db, "excluido", deleted_at=now_utc())

        assert deleted.user_id not in get_candidate_author_ids(db, viewer.user_id)

    def test_followed_public_account_appears_only_once(self, db):
        viewer = add_user(db, "viewer")
        public_author = add_user(db, "publico")
        add_follow(db, viewer, public_author)

        candidates = get_candidate_author_ids(db, viewer.user_id)

        assert candidates.count(public_author.user_id) == 1


class TestGetGeneralFeedQuery:
    def test_returns_only_recordas_from_given_authors(self, db):
        viewer = add_user(db, "viewer")
        included = add_user(db, "incluido")
        excluded = add_user(db, "fora")
        add_recorda(db, included)
        add_recorda(db, excluded)

        rows = db.execute(
            get_general_feed_query(viewer.user_id, [included.user_id])
        ).all()

        assert [row.Recorda.user_id for row in rows] == [included.user_id]

    def test_excludes_soft_deleted_recordas(self, db):
        viewer = add_user(db, "viewer")
        author = add_user(db, "autor")
        add_recorda(db, author, deleted_at=now_utc())

        rows = db.execute(
            get_general_feed_query(viewer.user_id, [author.user_id])
        ).all()

        assert rows == []

    def test_orders_by_newest_first(self, db):
        viewer = add_user(db, "viewer")
        author = add_user(db, "autor")
        older = add_recorda(db, author, created_at=datetime(2026, 1, 1, tzinfo=UTC))
        newer = add_recorda(db, author, created_at=datetime(2026, 1, 2, tzinfo=UTC))

        rows = db.execute(
            get_general_feed_query(viewer.user_id, [author.user_id])
        ).all()

        assert [row.Recorda.recorda_id for row in rows] == [
            newer.recorda_id,
            older.recorda_id,
        ]

    def test_maps_likes_count_and_is_liked_for_current_user(self, db):
        viewer = add_user(db, "viewer")
        author = add_user(db, "autor")
        other = add_user(db, "outro")
        recorda = add_recorda(db, author)

        db.add_all(
            [
                RecordaLike(user_id=viewer.user_id, recorda_id=recorda.recorda_id),
                RecordaLike(user_id=other.user_id, recorda_id=recorda.recorda_id),
            ]
        )
        db.commit()

        row = db.execute(get_general_feed_query(viewer.user_id, [author.user_id])).one()

        assert row.likes_count == 2
        assert row.is_liked is True

    def test_cursor_continues_without_repeating_items(self, db):
        viewer = add_user(db, "viewer")
        author = add_user(db, "autor")
        for day in (1, 2, 3):
            add_recorda(db, author, created_at=datetime(2026, 1, day, tzinfo=UTC))
        base_query = get_general_feed_query(viewer.user_id, [author.user_id])

        first_page = db.execute(base_query.limit(2)).all()
        last_seen = first_page[-1].Recorda
        second_page = db.execute(
            apply_cursor(base_query, last_seen.created_at, last_seen.recorda_id).limit(
                2
            )
        ).all()

        first_ids = {row.Recorda.recorda_id for row in first_page}
        second_ids = {row.Recorda.recorda_id for row in second_page}
        assert len(second_page) == 1
        assert first_ids.isdisjoint(second_ids)
