"""Testes do app/services/general_feed_service.py."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.db.seed_data import GENRE_SEED
from app.models import UserFavoriteArtist, UserFavoriteGenre
from app.models.follow import STATUS_PENDING
from app.repositories import general_feed_repository
from app.services import general_feed_service
from app.services.general_feed_service import InvalidCursorError, get_general_feed
from tests.factories import add_follow, add_recorda, add_user

ROCK_GENRE_ID = GENRE_SEED[0][0]
JAZZ_GENRE_ID = GENRE_SEED[1][0]


def _make_row(day: int = 1):
    recorda = SimpleNamespace(
        recorda_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        media_url="https://example.com/media.jpg",
        media_type="PHOTO",
        description=None,
        song_title="Song",
        song_artist_name="Artist",
        song_cover_url="https://example.com/cover.jpg",
        song_preview_url=None,
        created_at=datetime(2026, 1, day, tzinfo=UTC),
    )
    return SimpleNamespace(
        Recorda=recorda,
        username="autor",
        profile_picture_url=None,
        likes_count=0,
        is_liked=False,
    )


class TestGetGeneralFeedFlow:
    def test_invalid_cursor_raises_before_any_query(self):
        mock_db = MagicMock()

        with (
            patch.object(
                general_feed_repository, "get_candidate_author_ids"
            ) as candidates,
            pytest.raises(InvalidCursorError),
        ):
            get_general_feed(mock_db, uuid.uuid4(), cursor="invalido!!!", limit=20)

        candidates.assert_not_called()
        mock_db.execute.assert_not_called()

    def test_returns_empty_page_without_querying_feed_when_no_author_has_affinity(self):
        mock_db = MagicMock()

        with (
            patch.object(
                general_feed_repository,
                "get_candidate_author_ids",
                return_value=[uuid.uuid4(), uuid.uuid4()],
            ),
            patch.object(general_feed_service, "calculate_affinity", return_value=0.0),
        ):
            page = get_general_feed(mock_db, uuid.uuid4(), cursor=None, limit=20)

        assert page.items == []
        assert page.next_cursor is None
        mock_db.execute.assert_not_called()

    def test_only_authors_with_affinity_reach_the_feed_query(self):
        current_user_id = uuid.uuid4()
        with_affinity, without_affinity = uuid.uuid4(), uuid.uuid4()
        affinity_by_author = {with_affinity: 50.0, without_affinity: 0.0}
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = []

        with (
            patch.object(
                general_feed_repository,
                "get_candidate_author_ids",
                return_value=[with_affinity, without_affinity],
            ),
            patch.object(
                general_feed_service,
                "calculate_affinity",
                side_effect=lambda _db, _viewer, author: affinity_by_author[author],
            ),
            patch.object(
                general_feed_repository, "get_general_feed_query"
            ) as feed_query,
        ):
            get_general_feed(mock_db, current_user_id, cursor=None, limit=20)

        feed_query.assert_called_once_with(current_user_id, [with_affinity])

    def test_requests_one_extra_row_for_pagination_lookahead(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = []

        with (
            patch.object(
                general_feed_repository,
                "get_candidate_author_ids",
                return_value=[uuid.uuid4()],
            ),
            patch.object(
                general_feed_service, "calculate_affinity", return_value=100.0
            ),
            patch.object(
                general_feed_repository, "get_general_feed_query"
            ) as feed_query,
        ):
            get_general_feed(mock_db, uuid.uuid4(), cursor=None, limit=20)

        feed_query.return_value.limit.assert_called_once_with(21)

    def test_discards_extra_row_and_points_cursor_to_last_kept_row(self):
        rows = [_make_row(day) for day in (3, 2, 1)]
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = rows

        with (
            patch.object(
                general_feed_repository,
                "get_candidate_author_ids",
                return_value=[uuid.uuid4()],
            ),
            patch.object(
                general_feed_service, "calculate_affinity", return_value=100.0
            ),
            patch.object(general_feed_repository, "get_general_feed_query"),
        ):
            page = get_general_feed(mock_db, uuid.uuid4(), cursor=None, limit=2)

        assert len(page.items) == 2
        assert page.next_cursor is not None
        assert page.items[-1].recorda_id == rows[1].Recorda.recorda_id


def _add_favorite_genre(db, user, genre_id):
    db.add(UserFavoriteGenre(user_id=user.user_id, genre_id=genre_id))
    db.commit()


def _add_favorite_artist(db, user, deezer_artist_id):
    db.add(
        UserFavoriteArtist(
            user_id=user.user_id,
            deezer_artist_id=deezer_artist_id,
            artist_name=f"Artista {deezer_artist_id}",
        )
    )
    db.commit()


def _feed_author_ids(db, current_user):
    page = get_general_feed(db, current_user.user_id, cursor=None, limit=50)
    return {item.author.user_id for item in page.items}


class TestGetGeneralFeedIntegration:
    def test_applies_access_and_affinity_rules_together(self, db):
        viewer = add_user(db, "viewer")
        _add_favorite_genre(db, viewer, ROCK_GENRE_ID)
        _add_favorite_artist(db, viewer, "27")

        def author(username, genre_id, **fields):
            user = add_user(db, username, **fields)
            _add_favorite_genre(db, user, genre_id)
            add_recorda(db, user)
            return user

        public_with_affinity = author("publico_afim", ROCK_GENRE_ID)
        public_without_affinity = author("publico_sem_afim", JAZZ_GENRE_ID)
        private_followed = author("privado_seguido", ROCK_GENRE_ID, is_private=True)
        private_not_followed = author(
            "privado_nao_seguido", ROCK_GENRE_ID, is_private=True
        )
        private_pending = author("privado_pendente", ROCK_GENRE_ID, is_private=True)
        followed_without_affinity = author("seguido_sem_afim", JAZZ_GENRE_ID)
        artist_only_affinity = author("afim_por_artista", JAZZ_GENRE_ID)
        _add_favorite_artist(db, artist_only_affinity, "27")

        add_follow(db, viewer, private_followed)
        add_follow(db, viewer, private_pending, status=STATUS_PENDING)
        add_follow(db, viewer, followed_without_affinity)
        add_recorda(db, viewer)  # o próprio post nunca entra

        assert _feed_author_ids(db, viewer) == {
            public_with_affinity.user_id,
            private_followed.user_id,
            artist_only_affinity.user_id,
        }
        # Referências explícitas aos excluídos, para deixar claro o que a regra barra.
        excluded = {
            public_without_affinity.user_id,
            private_not_followed.user_id,
            private_pending.user_id,
            followed_without_affinity.user_id,
            viewer.user_id,
        }
        assert excluded.isdisjoint(_feed_author_ids(db, viewer))

    def test_user_without_musical_profile_gets_empty_feed(self, db):
        viewer = add_user(db, "viewer")
        other = add_user(db, "outro")
        _add_favorite_genre(db, other, ROCK_GENRE_ID)
        add_recorda(db, other)

        page = get_general_feed(db, viewer.user_id, cursor=None, limit=20)
        assert page.items == []
        assert page.next_cursor is None
