from datetime import UTC, datetime

import pytest

from app.schemas.retrospectives import RetrospectivePeriodQuery
from app.services import retrospective_service
from app.services.retrospective_service import (
    RetrospectiveNotFoundError,
    get_retrospective_details,
)
from tests.factories import add_comment, add_like, add_recorda, add_user


def test_get_available_periods(db):
    user_id = add_user(db, "Alice")
    different_user_id = add_user(db, "Bob")

    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))

    blank_result = retrospective_service.get_available_periods(
        db, different_user_id.user_id
    )
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert blank_result.periods == []
    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[0].total_memories == 1

    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 1, 1, 30))
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[1].year == 2023
    assert result.periods[1].month == 1
    assert result.periods[1].total_memories == 2


def test_get_available_periods_excludes_deleted(db):
    user_id = add_user(db, "Alice")

    add_recorda(
        db,
        user_id,
        created_at=datetime(2023, 1, 1, 3, 0, 0),
        deleted_at=datetime(2023, 2, 1, 3, 0, 0),
    )
    result = retrospective_service.get_available_periods(db, user_id.user_id)
    assert result.periods == []


def test_get_available_periods_ordering(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2022, 12, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))
    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2024, 3, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)

    assert result.periods[0].year == 2023
    assert result.periods[0].month == 2
    assert result.periods[1].year == 2023
    assert result.periods[1].month == 1
    assert result.periods[2].period_type == "YEARLY"
    assert result.periods[2].year == 2023
    assert result.periods[2].month is None
    assert result.periods[3].year == 2022
    assert result.periods[3].month == 12
    assert result.periods[4].period_type == "YEARLY"
    assert result.periods[4].year == 2022
    assert result.periods[4].month is None

    monthly_indexes_2023 = [
        i
        for i, period in enumerate(result.periods)
        if period.period_type == "MONTHLY" and period.year == 2023
    ]
    yearly_index_2023 = next(
        i
        for i, period in enumerate(result.periods)
        if period.period_type == "YEARLY" and period.year == 2023
    )

    assert monthly_indexes_2023
    assert max(monthly_indexes_2023) < yearly_index_2023


def test_get_available_test_is_preview(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2023, 1, 1, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 1, 3, 0, 0))

    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2023, 2, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)
    february = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 2
    )
    january = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 1
    )

    assert february.is_preview is True
    assert january.is_preview is False


def test_get_available_periods_includes_completed_year_only(db, monkeypatch):
    user_id = add_user(db, "Alice")

    add_recorda(db, user_id, created_at=datetime(2022, 1, 15, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2022, 12, 15, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 2, 10, 3, 0, 0))
    add_recorda(db, user_id, created_at=datetime(2023, 3, 10, 3, 0, 0))

    monkeypatch.setattr(
        retrospective_service,
        "now_utc",
        lambda: datetime(2023, 2, 15, 12, tzinfo=UTC),
    )

    result = retrospective_service.get_available_periods(db, user_id.user_id)

    annual_2022 = next(
        p for p in result.periods if p.period_type == "YEARLY" and p.year == 2022
    )
    february_2023 = next(
        p
        for p in result.periods
        if p.period_type == "MONTHLY" and p.year == 2023 and p.month == 2
    )

    assert annual_2022.label == "Ano de 2022"
    assert annual_2022.total_memories == 2
    assert annual_2022.is_preview is False
    assert february_2023.label == "Fevereiro 2023"
    assert february_2023.is_preview is True
    assert not any(p.period_type == "YEARLY" and p.year == 2023 for p in result.periods)
    assert not any(
        p.period_type == "MONTHLY" and p.year == 2023 and p.month == 3
        for p in result.periods
    )


def test_ensure_utc_returns_utc_datetime():
    dt_naive = datetime(2023, 1, 1, 12, 0, 0)
    dt_utc = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

    assert retrospective_service.ensure_utc(dt_naive) == dt_utc
    assert retrospective_service.ensure_utc(dt_utc) == dt_utc


def test_ensure_utc_preserves_timezone():
    dt_with_tz = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert retrospective_service.ensure_utc(dt_with_tz) == dt_with_tz


# --- Detalhes da retrospectiva (#149) ---

NOW = datetime(2026, 11, 15, 15, tzinfo=UTC)  # 15/11/2026 12:00 em São Paulo


def at(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def monthly(year: int, month: int) -> RetrospectivePeriodQuery:
    return RetrospectivePeriodQuery(period_type="MONTHLY", year=year, month=month)


def yearly(year: int) -> RetrospectivePeriodQuery:
    return RetrospectivePeriodQuery(period_type="YEARLY", year=year)


def test_details_aggregate_all_metrics_of_the_month(db):
    owner = add_user(db, "owner")
    fan = add_user(db, "fan")
    first = add_recorda(
        db,
        owner,
        created_at=at(2026, 10, 1, 15),
        deezer_track_id="1",
        song_artist_name="Artista A",
        song_genre_name="Pop",
        song_preview_url="https://cdn.deezer.com/preview.mp3",
    )
    add_recorda(
        db,
        owner,
        created_at=at(2026, 10, 2, 15),
        deezer_track_id="1",
        song_artist_name="Artista A",
        song_genre_name="Pop",
    )
    second_day = add_recorda(
        db,
        owner,
        created_at=at(2026, 10, 2, 20),
        deezer_track_id="2",
        song_artist_name="Artista B",
        song_genre_name="Rock",
    )
    add_recorda(
        db,
        owner,
        created_at=at(2026, 10, 5, 15),
        deezer_track_id="3",
        song_artist_name="Artista C",
    )
    # Excluída no dia 3: não conta e não emenda a sequência dos dias 1-2 com o 5.
    add_recorda(db, owner, created_at=at(2026, 10, 3, 15), deleted_at=at(2026, 10, 4))
    add_recorda(db, fan, created_at=at(2026, 10, 3, 15))
    add_like(db, fan, first)
    add_like(db, fan, second_day)
    add_comment(db, fan, first)

    result = get_retrospective_details(db, owner.user_id, monthly(2026, 10), now=NOW)

    assert result.label == "Outubro 2026"
    assert result.is_preview is False
    assert result.total_recordas == 4
    assert result.active_days == 3
    assert result.max_streak == 2
    assert [(a.artist_name, a.memory_count) for a in result.top_artists] == [
        ("Artista A", 2),
        ("Artista B", 1),
        ("Artista C", 1),
    ]
    assert [(g.genre_name, g.count, g.percentage) for g in result.top_genres] == [
        ("Pop", 2, 50.0),
        ("Rock", 1, 25.0),
    ]
    assert result.tagged_users == []
    assert result.engagement.likes_received == 2
    assert result.engagement.comments_received == 1
    assert result.featured_song.deezer_track_id == "1"
    assert result.featured_song.memory_count == 2
    assert result.featured_song.song_preview_url == "/api/v1/music/tracks/1/preview"


def test_current_month_is_preview(db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2026, 11, 10, 15))

    result = get_retrospective_details(db, owner.user_id, monthly(2026, 11), now=NOW)

    assert result.is_preview is True


def test_yearly_details_use_sao_paulo_year_bounds(db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2025, 1, 1, 2, 59))  # 31/12/2024 local
    add_recorda(db, owner, created_at=at(2025, 1, 1, 3))  # 01/01/2025 local
    add_recorda(db, owner, created_at=at(2026, 1, 1, 2, 59))  # 31/12/2025 local

    result = get_retrospective_details(db, owner.user_id, yearly(2025), now=NOW)

    assert result.label == "Ano de 2025"
    assert result.month is None
    assert result.total_recordas == 2


def test_top_artists_are_limited_to_five(db):
    owner = add_user(db, "owner")
    for day in range(1, 7):
        add_recorda(
            db,
            owner,
            created_at=at(2026, 10, day, 15),
            song_artist_name=f"Artista {day}",
        )

    result = get_retrospective_details(db, owner.user_id, monthly(2026, 10), now=NOW)

    assert len(result.top_artists) == 5


def test_featured_song_tie_goes_to_first_track_of_period(db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2026, 10, 1, 15), deezer_track_id="2")
    add_recorda(db, owner, created_at=at(2026, 10, 2, 15), deezer_track_id="1")

    result = get_retrospective_details(db, owner.user_id, monthly(2026, 10), now=NOW)

    assert result.featured_song.deezer_track_id == "2"


@pytest.mark.parametrize(
    "query",
    [
        monthly(2026, 9),  # sem Recordas
        monthly(2026, 12),  # mês futuro
        yearly(2026),  # ano ainda em andamento
    ],
)
def test_unavailable_periods_raise_not_found(db, query):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2026, 11, 10, 15))
    add_recorda(db, owner, created_at=at(2026, 9, 10, 15), deleted_at=at(2026, 9, 11))

    with pytest.raises(RetrospectiveNotFoundError):
        get_retrospective_details(db, owner.user_id, query, now=NOW)
