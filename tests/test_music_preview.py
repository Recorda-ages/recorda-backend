import pytest

from app.core.music_preview import public_preview_url, track_preview_path


def test_track_preview_path_points_at_the_renewing_route():
    assert track_preview_path("3135556") == "/api/v1/music/tracks/3135556/preview"


@pytest.mark.parametrize(
    ("track_id", "stored", "expected"),
    [
        (
            "3135556",
            "https://cdns-preview.deezer.com/p.mp3",
            "/api/v1/music/tracks/3135556/preview",
        ),
        # Already converted (e.g. a schema validated twice) stays the same.
        (
            "3135556",
            "/api/v1/music/tracks/3135556/preview",
            "/api/v1/music/tracks/3135556/preview",
        ),
        ("3135556", None, None),
        ("3135556", "", None),
        (None, "https://cdns-preview.deezer.com/p.mp3", None),
    ],
)
def test_public_preview_url(track_id, stored, expected):
    assert public_preview_url(track_id, stored) == expected
