from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.affinity_service import calculate_affinity


def _genre(genre_id):
    return MagicMock(genre_id=genre_id)


def _artist(deezer_artist_id):
    return MagicMock(deezer_artist_id=deezer_artist_id)


class TestCalculateAffinity:
    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_no_overlap_results_in_zero_affinity(self, mock_genres, mock_artists):
        mock_genres.side_effect = [[_genre(uuid4())], [_genre(uuid4())]]
        mock_artists.side_effect = [[_artist("artist-1")], [_artist("artist-2")]]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result == 0.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_genre_overlap_results_in_affinity_greater_than_zero(
        self, mock_genres, mock_artists
    ):
        shared_genre = uuid4()
        mock_genres.side_effect = [
            [_genre(shared_genre)],
            [_genre(shared_genre), _genre(uuid4())],
        ]
        mock_artists.side_effect = [[], []]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result > 0.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_artist_overlap_results_in_affinity_greater_than_zero(
        self, mock_genres, mock_artists
    ):
        mock_genres.side_effect = [[], []]
        mock_artists.side_effect = [
            [_artist("artist-1")],
            [_artist("artist-1"), _artist("artist-2")],
        ]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result > 0.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_identical_profiles_result_in_full_affinity(self, mock_genres, mock_artists):
        genre_id = uuid4()
        mock_genres.side_effect = [[_genre(genre_id)], [_genre(genre_id)]]
        mock_artists.side_effect = [[_artist("artist-1")], [_artist("artist-1")]]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result == 100.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_reference_is_the_smaller_profile(self, mock_genres, mock_artists):
        shared_genre = uuid4()
        mock_genres.side_effect = [
            [_genre(shared_genre)],
            [_genre(shared_genre), _genre(uuid4()), _genre(uuid4())],
        ]
        mock_artists.side_effect = [[], [_artist("artist-1")]]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        # referência = min(1, 4) = 1; hits = 1 -> 100%
        assert result == 100.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_empty_profile_results_in_zero_affinity(self, mock_genres, mock_artists):
        mock_genres.side_effect = [[], [_genre(uuid4())]]
        mock_artists.side_effect = [[], [_artist("artist-1")]]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result == 0.0

    @patch("app.services.affinity_service.get_artists")
    @patch("app.services.affinity_service.get_genres")
    def test_both_empty_profiles_result_in_zero_affinity(self, mock_genres, mock_artists):
        mock_genres.side_effect = [[], []]
        mock_artists.side_effect = [[], []]

        result = calculate_affinity(db=None, user_id_a=uuid4(), user_id_b=uuid4())

        assert result == 0.0