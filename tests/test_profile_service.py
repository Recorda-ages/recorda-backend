"""Unit tests for the profile header contract (ProfileRead)."""

from datetime import UTC, date, datetime, timedelta

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
TODAY = date(2026, 10, 18)
NOW = datetime(2026, 10, 18, 15, 0, tzinfo=UTC)  # 12:00 em São Paulo


@pytest.fixture
def owner(db):
    return add_user(db, "gabriel", is_private=True, **FAVORITE_SONG)


@pytest.fixture
def fixed_now(monkeypatch):
    monkeypatch.setattr(profile_service, "now_utc", lambda: NOW)


def _days_ago(*offsets: int) -> set[date]:
    return {TODAY - timedelta(days=offset) for offset in offsets}


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
    assert profile.streak.current_days == 0
    assert profile.streak.published_today is False


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


@pytest.mark.parametrize(
    ("days", "expected_days", "expected_today"),
    [
        pytest.param(set(), 0, False, id="sem-publicacoes"),
        pytest.param(_days_ago(0), 1, True, id="so-hoje"),
        pytest.param(_days_ago(0, 1), 2, True, id="ontem-e-hoje-soma-1"),
        pytest.param(_days_ago(1), 1, False, id="so-ontem-ainda-vale"),
        pytest.param(_days_ago(1, 2, 3), 3, False, id="sequencia-ate-ontem"),
        pytest.param(_days_ago(2), 0, False, id="dia-inteiro-sem-publicar-zera"),
        pytest.param(_days_ago(0, 1, 3, 4), 2, True, id="buraco-interrompe"),
    ],
)
def test_calculate_streak(days, expected_days, expected_today):
    streak = profile_service.calculate_streak(days, TODAY)

    assert streak.current_days == expected_days
    assert streak.published_today is expected_today


def test_build_streak_counts_consecutive_publication_days(db, owner, fixed_now):
    add_recorda(db, owner, created_at=NOW)
    add_recorda(db, owner, created_at=NOW - timedelta(days=1))

    streak = profile_service.build_streak(db, owner.user_id)

    assert streak.current_days == 2
    assert streak.published_today is True


def test_build_streak_counts_several_recordas_on_same_day_once(db, owner, fixed_now):
    add_recorda(db, owner, created_at=NOW)
    add_recorda(db, owner, created_at=NOW - timedelta(hours=2))

    assert profile_service.build_streak(db, owner.user_id).current_days == 1


def test_build_streak_keeps_day_of_deleted_recorda(db, owner, fixed_now):
    add_recorda(db, owner, created_at=NOW - timedelta(days=1), deleted_at=NOW)
    add_recorda(db, owner, created_at=NOW)

    assert profile_service.build_streak(db, owner.user_id).current_days == 2


def test_build_streak_ignores_other_users(db, owner, fixed_now):
    other = add_user(db, "camila")
    add_recorda(db, other, created_at=NOW)

    streak = profile_service.build_streak(db, owner.user_id)

    assert streak.current_days == 0
    assert streak.published_today is False


def test_build_streak_uses_sao_paulo_day(db, owner, fixed_now):
    # 18/10 01:30 UTC = 17/10 22:30 em São Paulo: conta como ontem, não hoje.
    add_recorda(db, owner, created_at=datetime(2026, 10, 18, 1, 30, tzinfo=UTC))

    streak = profile_service.build_streak(db, owner.user_id)

    assert streak.current_days == 1
    assert streak.published_today is False
