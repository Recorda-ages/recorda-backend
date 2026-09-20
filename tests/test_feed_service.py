"""Testes do app/services/feed_service.py."""

import base64
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.feed import FeedItem
from app.services.feed_service import (
    InvalidCursorError,
    _decode_cursor,
    _encode_cursor,
    _to_feed_item,
    get_following_feed,
)


def _make_row(**overrides):
    """Monta um fake Row do jeito que get_following_feed_query devolveria."""
    recorda = SimpleNamespace(
        recorda_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        media_url="https://example.com/media.jpg",
        media_type="PHOTO",
        description="uma recordação",
        song_title="Song",
        song_artist_name="Artist",
        song_cover_url="https://example.com/cover.jpg",
        song_preview_url=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    row = SimpleNamespace(
        Recorda=recorda,
        username="raffa",
        profile_picture_url=None,
        likes_count=0,
        is_liked=False,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class TestEncodeDecodeCursor:
    def test_round_trip(self):
        created_at = datetime(2026, 3, 15, 12, 30, tzinfo=UTC)
        recorda_id = uuid.uuid4()

        cursor = _encode_cursor(created_at, recorda_id)
        decoded_created_at, decoded_recorda_id = _decode_cursor(cursor)

        assert decoded_created_at == created_at
        assert decoded_recorda_id == recorda_id

    def test_decode_invalid_base64_raises_invalid_cursor_error(self):
        with pytest.raises(InvalidCursorError):
            _decode_cursor("isso não é base64 válido!!!")

    def test_decode_missing_separator_raises_invalid_cursor_error(self):
        malformed = base64.urlsafe_b64encode(b"sem separador").decode()

        with pytest.raises(InvalidCursorError):
            _decode_cursor(malformed)

    def test_decode_invalid_uuid_raises_invalid_cursor_error(self):
        raw = "2026-01-01T00:00:00+00:00|nao-e-um-uuid"
        malformed = base64.urlsafe_b64encode(raw.encode()).decode()

        with pytest.raises(InvalidCursorError):
            _decode_cursor(malformed)


class TestToFeedItem:
    def test_maps_row_to_feed_item(self):
        row = _make_row()

        item = _to_feed_item(row)

        assert isinstance(item, FeedItem)
        assert item.recorda_id == row.Recorda.recorda_id
        assert item.author.user_id == row.Recorda.user_id
        assert item.author.username == row.username
        assert item.author.profile_picture_url == row.profile_picture_url
        assert item.likes_count == row.likes_count
        assert item.is_liked == row.is_liked


class TestGetFollowingFeed:
    def test_returns_all_rows_when_under_limit(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = [_make_row() for _ in range(3)]

        result = get_following_feed(mock_db, uuid.uuid4(), cursor=None, limit=20)

        assert len(result.items) == 3
        assert result.next_cursor is None

    def test_discards_extra_row_and_sets_next_cursor(self):
        # limit=2, mas o repository devolve 3 (limit + 1) — sinaliza
        # que existe próxima página.
        rows = [_make_row() for _ in range(3)]
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = rows

        result = get_following_feed(mock_db, uuid.uuid4(), cursor=None, limit=2)

        assert len(result.items) == 2
        assert result.next_cursor is not None

    def test_next_cursor_points_to_last_kept_row_not_the_extra_one(self):
        rows = [
            _make_row(
                Recorda=SimpleNamespace(
                    recorda_id=uuid.uuid4(),
                    user_id=uuid.uuid4(),
                    media_url="u",
                    media_type="PHOTO",
                    description=None,
                    song_title="s",
                    song_artist_name="a",
                    song_cover_url="c",
                    song_preview_url=None,
                    created_at=datetime(2026, 1, day, tzinfo=UTC),
                )
            )
            for day in (3, 2, 1)  # created_at decrescente, como o ORDER BY real
        ]
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = rows

        result = get_following_feed(mock_db, uuid.uuid4(), cursor=None, limit=2)

        last_kept_row = rows[1]  # segunda linha é a última da página (2 itens)
        _, decoded_recorda_id = _decode_cursor(result.next_cursor)
        assert decoded_recorda_id == last_kept_row.Recorda.recorda_id

    def test_invalid_cursor_raises_before_hitting_the_database(self):
        mock_db = MagicMock()

        with pytest.raises(InvalidCursorError):
            get_following_feed(mock_db, uuid.uuid4(), cursor="invalido!!!", limit=20)

        mock_db.execute.assert_not_called()

    def test_requests_one_extra_row_for_pagination_lookahead(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = []

        get_following_feed(mock_db, uuid.uuid4(), cursor=None, limit=20)

        executed_query = mock_db.execute.call_args[0][0]
        compiled = str(
            executed_query.compile(compile_kwargs={"literal_binds": True})
        ).upper()
        assert "LIMIT 21" in compiled
