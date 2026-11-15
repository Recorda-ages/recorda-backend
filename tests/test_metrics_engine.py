from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.schemas.metrics import MetricsPeriod, RecordaMetrics
from app.services.metrics.context import MetricsContext
from app.services.metrics.engine import MetricsEngine
from tests.factories import add_recorda, add_user, auth_headers

NOW = datetime(2026, 11, 7, 15, tzinfo=UTC)
TODAY = date(2026, 11, 7)


@pytest.mark.parametrize(
    ("offsets", "current", "maximum"),
    [
        ([0, 1, 2], 3, 3),
        ([1, 2], 2, 2),
        ([2, 3], 0, 2),
        ([0, 2, 3, 4], 1, 3),
        ([], 0, 0),
        ([0, 0, 1], 2, 2),
    ],
)
def test_daily_streak(offsets, current, maximum):
    days = frozenset(TODAY - timedelta(days=n) for n in offsets)
    result = MetricsEngine().calculate("streak", MetricsContext((), days, TODAY))
    assert result.current_streak == current
    assert result.max_streak == maximum
    assert result.last_post_date == (max(days) if days else None)


@pytest.mark.parametrize(
    "database", ["db", pytest.param("pg_db", marks=pytest.mark.postgres)]
)
def test_profile_filters_deleted_foreign_and_future_recordas(request, database):
    db = request.getfixturevalue(database)
    user = add_user(db, "owner")
    other = add_user(db, "other")
    for artist, genre in [("B", "Pop"), ("A", "Rock"), ("A", None)]:
        add_recorda(
            db, user, created_at=NOW, song_artist_name=artist, song_genre_name=genre
        )
    add_recorda(db, user, created_at=NOW, deleted_at=NOW, song_artist_name="Deleted")
    add_recorda(db, other, created_at=NOW, song_artist_name="Foreign")
    add_recorda(db, user, created_at=NOW + timedelta(days=1), song_artist_name="Future")
    result = MetricsEngine().profile(db, user.user_id, now=NOW)
    assert result.top_artist.artist_name == "A"
    assert result.top_artist.memory_count == 2
    assert result.top_artist.image_url == "https://e.deezer.com/cover.jpg"
    assert [(g.genre_name, g.count, g.percentage) for g in result.top_genres] == [
        ("Pop", 1, 33.33),
        ("Rock", 1, 33.33),
    ]
    assert result.streak.current_streak_days == 1
    assert result.streak.last_post_date == TODAY


@pytest.mark.parametrize(
    ("period", "length"),
    [
        (MetricsPeriod.LAST_30_DAYS, 30),
        (MetricsPeriod.LAST_90_DAYS, 90),
        (MetricsPeriod.LAST_YEAR, 365),
    ],
)
@pytest.mark.parametrize(
    "database", ["db", pytest.param("pg_db", marks=pytest.mark.postgres)]
)
def test_period_starts_at_local_midnight(request, database, period, length):
    db = request.getfixturevalue(database)
    user = add_user(db, "owner")
    start = datetime(2026, 11, 7, 3, tzinfo=UTC) - timedelta(days=length - 1)
    add_recorda(
        db,
        user,
        created_at=start - timedelta(microseconds=1),
        song_artist_name="Excluded",
    )
    add_recorda(db, user, created_at=start, song_artist_name="Included")
    result = MetricsEngine().profile(db, user.user_id, period, now=NOW)
    assert result.top_artist.artist_name == "Included"
    assert result.top_artist.memory_count == 1


def test_empty_profile(db):
    user = add_user(db, "owner")
    result = MetricsEngine().profile(db, user.user_id, now=NOW)
    assert result.model_dump(mode="json") == {
        "period": "all_time",
        "total_recordas": 0,
        "top_artist": None,
        "top_artists": [],
        "top_genres": [],
        "monthly_distribution": [],
        "streak": {"current_streak_days": 0, "last_post_date": None},
    }


@pytest.mark.parametrize(
    "database", ["db", pytest.param("pg_db", marks=pytest.mark.postgres)]
)
def test_streak_local_midnight_and_deleted_gap(request, database):
    db = request.getfixturevalue(database)
    user = add_user(db, "owner")
    add_recorda(
        db, user, created_at=datetime(2026, 11, 7, 2, 59, tzinfo=UTC)
    )  # yesterday
    add_recorda(db, user, created_at=datetime(2026, 11, 7, 3, tzinfo=UTC))  # today
    add_recorda(db, user, created_at=NOW - timedelta(days=2), deleted_at=NOW)
    add_recorda(db, user, created_at=NOW - timedelta(days=3))
    assert (
        MetricsEngine().profile(db, user.user_id, now=NOW).streak.current_streak_days
        == 2
    )


def test_profile_total_top_artists_and_monthly_distribution(db):
    user = add_user(db, "owner")
    other = add_user(db, "other")
    stamps = [
        datetime(2026, 9, 30, 12, tzinfo=UTC),
        datetime(2026, 10, 1, 2, 59, tzinfo=UTC),
        datetime(2026, 10, 1, 3, tzinfo=UTC),
        datetime(2026, 11, 7, 12, tzinfo=UTC),
    ]
    artists = ["A", "A", "B", "C"]
    for stamp, artist in zip(stamps, artists, strict=True):
        add_recorda(db, user, created_at=stamp, song_artist_name=artist)
    for index in range(6):
        add_recorda(
            db, user, created_at=NOW, song_artist_name=f"Z{index}", deleted_at=NOW
        )
    add_recorda(db, other, created_at=NOW, song_artist_name="Foreign")
    result = MetricsEngine().profile(db, user.user_id, now=NOW)
    assert result.total_recordas == 4
    assert [a.artist_name for a in result.top_artists] == ["A", "B", "C"]
    assert result.top_artists[0] == result.top_artist
    assert [(m.year, m.month, m.count) for m in result.monthly_distribution] == [
        (2026, 9, 2),
        (2026, 10, 1),
        (2026, 11, 1),
    ]


def test_profile_top_artists_are_capped(db):
    user = add_user(db, "owner")
    for index in range(7):
        add_recorda(db, user, created_at=NOW, song_artist_name=f"Artist {index}")
    result = MetricsEngine().profile(db, user.user_id, now=NOW)
    assert len(result.top_artists) == 5
    assert result.total_recordas == 7


def test_streak_not_truncated_by_period(db):
    user = add_user(db, "owner")
    for n in range(35):
        add_recorda(db, user, created_at=NOW - timedelta(days=n))
    result = MetricsEngine().profile(
        db, user.user_id, MetricsPeriod.LAST_30_DAYS, now=NOW
    )
    assert result.top_artist.memory_count == 30
    assert result.streak.current_streak_days == 35


def test_strategies_and_injection():
    user = uuid4()
    context = MetricsContext((), frozenset(), TODAY, (user, user), likes=3, comments=2)
    engine = MetricsEngine()
    assert engine.calculate("total_recordas", context) == 0
    assert engine.calculate("tagged_users", context) == {user: 2}
    assert engine.calculate("engagement", context).total == 5
    assert engine.calculate("top_genres", context) == []
    assert engine.calculate("top_artists", context) == []

    class Constant:
        def calculate(self, context: MetricsContext) -> int:
            return 42

    assert (
        MetricsEngine({"total_recordas": Constant()}).calculate(
            "total_recordas", context
        )
        == 42
    )


def test_artist_tie_and_latest_cover(db):
    user = add_user(db, "owner")
    add_recorda(db, user, created_at=NOW - timedelta(days=1), song_artist_name="B")
    add_recorda(db, user, created_at=NOW, song_artist_name="A", song_cover_url="latest")
    result = MetricsEngine().profile(db, user.user_id, now=NOW)
    assert result.top_artist.artist_name == "A"
    assert result.top_artist.image_url == "latest"


def test_metrics_route(client, db):
    user = add_user(db, "owner")
    response = client.get(
        "/api/v1/users/me/metrics?bundle=profile", headers=auth_headers(user)
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "period",
        "total_recordas",
        "top_artist",
        "top_artists",
        "top_genres",
        "monthly_distribution",
        "streak",
    }
    for period in MetricsPeriod:
        assert (
            client.get(
                f"/api/v1/users/me/metrics?period={period}", headers=auth_headers(user)
            ).status_code
            == 200
        )


@pytest.mark.parametrize("query", ["period=30d", "bundle=retrospective"])
def test_invalid_metrics_parameters(client, db, query):
    user = add_user(db, "owner")
    assert (
        client.get(
            f"/api/v1/users/me/metrics?{query}", headers=auth_headers(user)
        ).status_code
        == 422
    )


def test_metrics_requires_jwt(client):
    assert client.get("/api/v1/users/me/metrics").status_code == 401
    assert (
        client.get(
            "/api/v1/users/me/metrics", headers={"Authorization": "Bearer invalid"}
        ).status_code
        == 401
    )


@pytest.mark.parametrize("same_timestamp", [False, True])
def test_artist_cover_is_independent_of_input_order(same_timestamp):
    newest = RecordaMetrics(
        recorda_id=UUID(int=2),
        created_at=NOW,
        song_artist_name="Artist",
        song_cover_url="latest-cover",
        song_genre_name=None,
    )
    older = RecordaMetrics(
        recorda_id=UUID(int=1),
        created_at=NOW if same_timestamp else NOW - timedelta(days=1),
        song_artist_name="Artist",
        song_cover_url="older-cover",
        song_genre_name=None,
    )
    for recordas in [(newest, older), (older, newest)]:
        context = MetricsContext(recordas, frozenset({TODAY}), TODAY)
        artists = MetricsEngine().calculate("top_artists", context)
        assert artists[0].image_url == "latest-cover"
