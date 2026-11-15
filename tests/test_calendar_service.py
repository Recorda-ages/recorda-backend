"""Calendário mensal de memórias: agrupamento por dia local em São Paulo (US37)."""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.core.time import now_utc
from app.models import RecordaLike
from app.models.app_user import STATUS_SUSPENDED
from app.services import calendar_service
from app.services.calendar_service import get_monthly_calendar
from tests.factories import add_comment, add_recorda, add_user


@pytest.fixture(params=["db", pytest.param("pg_db", marks=pytest.mark.postgres)])
def daily_db(request):
    """Exercita o mesmo contrato diário em SQLite e PostgreSQL migrado."""
    return request.getfixturevalue(request.param)


def at(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_empty_month(db):
    owner = add_user(db, "owner")

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.model_dump() == {
        "year": 2026,
        "month": 11,
        "total_memories": 0,
        "active_days_count": 0,
        "days": [],
    }


def test_groups_same_day_and_uses_first_recorda_as_thumbnail(db):
    owner = add_user(db, "owner")
    # Inseridas fora de ordem: a primeira do dia vem do created_at, não da inserção.
    add_recorda(db, owner, created_at=at(2026, 11, 10, 20), media_url="/m/later.jpg")
    first = add_recorda(
        db,
        owner,
        created_at=at(2026, 11, 10, 13),
        media_url="/m/first.mp4",
        media_type="VIDEO",
    )

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.total_memories == 2
    assert result.active_days_count == 1
    [day] = result.days
    assert day.date == date(2026, 11, 10)
    assert day.day == 10
    assert day.count == 2
    assert day.first_recorda_id == first.recorda_id
    assert day.thumbnail_url == "/m/first.mp4"
    assert day.media_type == "VIDEO"


def test_late_night_publication_stays_on_local_day(db):
    owner = add_user(db, "owner")
    # 23:59 de 10/11 em São Paulo já é 11/11 em UTC.
    add_recorda(db, owner, created_at=at(2026, 11, 11, 2, 59))

    [day] = get_monthly_calendar(db, owner.user_id, 2026, 11).days

    assert day.date == date(2026, 11, 10)


def test_month_bounds_follow_sao_paulo_midnight(db):
    owner = add_user(db, "owner")
    add_recorda(db, owner, created_at=at(2026, 11, 1, 2, 59, 59))  # 31/10 23:59:59
    add_recorda(db, owner, created_at=at(2026, 11, 1, 3))  # 01/11 00:00
    add_recorda(db, owner, created_at=at(2026, 12, 1, 2, 59, 59))  # 30/11 23:59:59
    add_recorda(db, owner, created_at=at(2026, 12, 1, 3))  # 01/12 00:00

    november = get_monthly_calendar(db, owner.user_id, 2026, 11)
    october = get_monthly_calendar(db, owner.user_id, 2026, 10)
    december = get_monthly_calendar(db, owner.user_id, 2026, 12)

    assert [d.date for d in november.days] == [date(2026, 11, 1), date(2026, 11, 30)]
    assert november.total_memories == 2
    assert [d.date for d in october.days] == [date(2026, 10, 31)]
    assert [d.date for d in december.days] == [date(2026, 12, 1)]


def test_ignores_deleted_recordas_and_other_users(db):
    owner = add_user(db, "owner")
    other = add_user(db, "other")
    kept = add_recorda(db, owner, created_at=at(2026, 11, 5, 15))
    add_recorda(db, owner, created_at=at(2026, 11, 5, 12), deleted_at=now_utc())
    add_recorda(db, owner, created_at=at(2026, 11, 6, 12), deleted_at=now_utc())
    add_recorda(db, other, created_at=at(2026, 11, 5, 10))

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert result.total_memories == 1
    [day] = result.days
    assert (day.day, day.count, day.first_recorda_id) == (5, 1, kept.recorda_id)


def test_days_are_sorted_and_totals_add_up(db):
    owner = add_user(db, "owner")
    for created_at in [
        at(2026, 11, 20, 15),
        at(2026, 11, 3, 15),
        at(2026, 11, 20, 16),
        at(2026, 11, 12, 15),
        at(2026, 11, 3, 16),
    ]:
        add_recorda(db, owner, created_at=created_at)

    result = get_monthly_calendar(db, owner.user_id, 2026, 11)

    assert [(d.day, d.count) for d in result.days] == [(3, 2), (12, 1), (20, 2)]
    assert result.total_memories == 5
    assert result.active_days_count == 3


def test_daily_memories_without_history(daily_db):
    db = daily_db
    owner = add_user(db, "owner")

    result = calendar_service.get_daily_memories(db, owner.user_id, date(2026, 11, 7))

    assert result.model_dump(mode="json") == {
        "date": "2026-11-07",
        "total_count": 0,
        "memories": [],
        "previous_date_with_memories": None,
        "next_date_with_memories": None,
    }


def test_daily_memories_are_chronological_with_safe_previews_and_local_time(daily_db):
    db = daily_db
    owner = add_user(db, "owner", profile_picture_url="/m/avatar.jpg")
    last = add_recorda(db, owner, created_at=at(2026, 11, 8, 2, 59))
    first = add_recorda(
        db,
        owner,
        created_at=at(2026, 11, 7, 3),
        media_type="VIDEO",
        media_url="/m/first.mp4",
        song_preview_url="https://expired.deezer.test/preview.mp3",
        song_genre_name="Rock",
    )
    add_recorda(db, owner, created_at=at(2026, 11, 7, 2, 59, 59))
    add_recorda(db, owner, created_at=at(2026, 11, 8, 3))
    add_recorda(db, owner, created_at=at(2026, 11, 7, 15), deleted_at=now_utc())
    stranger = add_user(db, "stranger")
    add_recorda(db, stranger, created_at=at(2026, 11, 7, 12))

    result = calendar_service.get_daily_memories(db, owner.user_id, date(2026, 11, 7))

    assert result.total_count == 2
    assert [m.recorda_id for m in result.memories] == [
        first.recorda_id,
        last.recorda_id,
    ]
    video, photo = result.memories
    assert video.author.model_dump() == {
        "user_id": owner.user_id,
        "username": "owner",
        "avatar_url": "/m/avatar.jpg",
    }
    assert (video.media_type, video.media_url) == ("VIDEO", "/m/first.mp4")
    assert video.description == "By Disturbed"
    assert video.song_genre_name == "Rock"
    assert video.song_preview_url == "/api/v1/music/tracks/3135556/preview"
    assert photo.song_preview_url is None
    assert [m.formatted_time for m in result.memories] == ["00:00", "23:59"]
    assert video.created_at == at(2026, 11, 7, 3)
    assert (video.likes_count, video.comments_count, video.is_liked) == (0, 0, False)


@pytest.mark.parametrize(
    ("target", "previous", "following", "count"),
    [
        (date(2026, 1, 1), date(2025, 12, 31), date(2026, 2, 1), 2),
        (date(2026, 1, 15), date(2026, 1, 1), date(2026, 2, 1), 0),
        (date(2025, 12, 1), None, date(2025, 12, 31), 0),
        (date(2025, 12, 31), None, date(2026, 1, 1), 1),
        (date(2026, 2, 1), date(2026, 1, 1), None, 1),
        (date(2026, 3, 1), date(2026, 2, 1), None, 0),
    ],
)
def test_daily_navigation_uses_closest_live_local_dates(
    daily_db, target, previous, following, count
):
    db = daily_db
    owner = add_user(db, "owner")
    # UTC em 01/01 ainda é 31/12 em São Paulo.
    add_recorda(db, owner, created_at=at(2026, 1, 1, 2, 59, 59))
    add_recorda(db, owner, created_at=at(2026, 1, 1, 3))
    add_recorda(db, owner, created_at=at(2026, 1, 2, 2, 59, 59))
    add_recorda(db, owner, created_at=at(2026, 2, 1, 3))
    for timestamp in [at(2026, 1, 10, 12), at(2026, 1, 20, 12)]:
        add_recorda(db, owner, created_at=timestamp, deleted_at=now_utc())
    stranger = add_user(db, "stranger")
    add_recorda(db, stranger, created_at=at(2026, 1, 14, 12))
    add_recorda(db, stranger, created_at=at(2026, 1, 16, 12))

    result = calendar_service.get_daily_memories(db, owner.user_id, target)

    assert result.previous_date_with_memories == previous
    assert result.next_date_with_memories == following
    assert result.total_count == count


def test_daily_engagement_counts_visible_comments_and_current_user_likes(daily_db):
    db = daily_db
    owner = add_user(db, "owner")
    friend = add_user(db, "friend")
    suspended = add_user(db, "suspended", status=STATUS_SUSPENDED)
    deleted = add_user(db, "deleted", deleted_at=now_utc())
    first = add_recorda(db, owner, created_at=at(2026, 11, 7, 12))
    second = add_recorda(db, owner, created_at=at(2026, 11, 7, 13))
    outside_day = add_recorda(db, owner, created_at=at(2026, 11, 8, 12))
    for user, recorda in [(owner, first), (friend, first), (friend, second)]:
        db.add(RecordaLike(user_id=user.user_id, recorda_id=recorda.recorda_id))
    db.commit()
    add_comment(db, owner, first)
    add_comment(db, friend, first)
    add_comment(db, friend, first, deleted_at=now_utc())
    add_comment(db, suspended, first)
    add_comment(db, deleted, first)
    add_comment(db, friend, outside_day)

    result = calendar_service.get_daily_memories(db, owner.user_id, date(2026, 11, 7))

    assert [(m.likes_count, m.is_liked, m.comments_count) for m in result.memories] == [
        (2, True, 2),
        (1, False, 0),
    ]


def test_daily_order_is_deterministic_for_equal_timestamps(daily_db):
    db = daily_db
    owner = add_user(db, "owner")
    for recorda_id in [UUID(int=2), UUID(int=1)]:
        add_recorda(db, owner, recorda_id=recorda_id, created_at=at(2026, 11, 7, 12))

    result = calendar_service.get_daily_memories(db, owner.user_id, date(2026, 11, 7))

    assert [memory.recorda_id for memory in result.memories] == [
        UUID(int=1),
        UUID(int=2),
    ]


def test_daily_memories_include_repeated_hour_at_end_of_daylight_saving(daily_db):
    db = daily_db
    owner = add_user(db, "owner")
    # 16/02/2019 teve 25h em São Paulo; a última hora se repetiu.
    previous = add_recorda(db, owner, created_at=at(2019, 2, 16, 1, 59, 59))
    first = add_recorda(db, owner, created_at=at(2019, 2, 16, 2))
    repeated_hour = add_recorda(db, owner, created_at=at(2019, 2, 17, 2, 30))
    following = add_recorda(db, owner, created_at=at(2019, 2, 17, 3))

    result = calendar_service.get_daily_memories(db, owner.user_id, date(2019, 2, 16))

    assert [memory.recorda_id for memory in result.memories] == [
        first.recorda_id,
        repeated_hour.recorda_id,
    ]
    assert [memory.formatted_time for memory in result.memories] == ["00:00", "23:30"]
    assert result.previous_date_with_memories == date(2019, 2, 15)
    assert result.next_date_with_memories == date(2019, 2, 17)
    assert previous.recorda_id not in [m.recorda_id for m in result.memories]
    assert following.recorda_id not in [m.recorda_id for m in result.memories]
