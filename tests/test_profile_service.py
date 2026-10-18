"""Unit tests for the profile header contract (ProfileRead)."""

import pytest

from app.core.time import now_utc
from app.models.follow import STATUS_PENDING
from app.services import profile_service
from tests.factories import add_follow, add_recorda, add_user

FAVORITE_SONG = {
    "fav_song_deezer_track_id": "3135556",
    "fav_song_title": "Harder, Better, Faster, Stronger",
    "fav_song_artist_name": "Daft Punk",
    "fav_song_cover_url": "https://e.deezer.com/cover.jpg",
    "fav_song_preview_url": "https://cdns-preview.deezer.com/p.mp3",
}


@pytest.fixture
def owner(db):
    return add_user(db, "gabriel", is_private=True, **FAVORITE_SONG)


def test_build_profile_returns_identity_and_favorite_song(db, owner):
    profile = profile_service.build_profile(db, owner, owner)

    assert profile.user_id == owner.user_id
    assert profile.username == "gabriel"
    assert profile.name == owner.name
    assert profile.is_private is True
    assert profile.favorite_song.deezer_track_id == "3135556"
    assert profile.favorite_song.preview_url == "/api/v1/music/tracks/3135556/preview"


def test_build_profile_marks_own_profile(db, owner):
    profile = profile_service.build_profile(db, owner, owner)

    assert profile.relationship.is_self is True
    assert profile.relationship.follow_status == "nenhuma"
    assert profile.relationship.follow_id is None
    assert profile.can_view_content is True
    assert profile.streak is None


def test_build_profile_counts_only_live_content_and_accepted_follows(db, owner):
    add_recorda(db, owner)
    add_recorda(db, owner, deleted_at=now_utc())
    add_follow(db, add_user(db, "fan"), owner)
    add_follow(db, add_user(db, "waiting"), owner, status=STATUS_PENDING)
    add_follow(db, owner, add_user(db, "idol"))

    counts = profile_service.build_profile(db, owner, owner).counts

    assert counts.recordas == 1
    assert counts.followers == 1
    assert counts.following == 1


def test_build_profile_without_preview_returns_null_preview(db):
    user = add_user(db, "nopreview", **{**FAVORITE_SONG, "fav_song_preview_url": None})

    assert (
        profile_service.build_profile(db, user, user).favorite_song.preview_url is None
    )


@pytest.mark.parametrize(
    "missing_field",
    [
        "fav_song_deezer_track_id",
        "fav_song_title",
        "fav_song_artist_name",
        "fav_song_cover_url",
    ],
)
def test_build_profile_requires_completed_onboarding(db, missing_field):
    user = add_user(db, "incomplete", **{**FAVORITE_SONG, missing_field: None})

    with pytest.raises(profile_service.IncompleteProfileError):
        profile_service.build_profile(db, user, user)


def test_build_profile_rejects_third_party_until_us29(db, owner):
    viewer = add_user(db, "viewer", **FAVORITE_SONG)

    with pytest.raises(NotImplementedError):
        profile_service.build_profile(db, owner, viewer)
