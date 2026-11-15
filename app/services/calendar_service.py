"""Calendário mensal e memórias diárias do usuário autenticado (US37)."""

from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.music_preview import public_preview_url
from app.core.time import local_day_bounds, local_month_bounds, to_local
from app.models import Recorda
from app.repositories import (
    comment_repository,
    recorda_like_repository,
    recorda_repository,
    user_repository,
)
from app.schemas.calendar import (
    CalendarDaySummary,
    DailyMemoriesResponse,
    DayRecordaDetail,
    MonthlyCalendarResponse,
)
from app.schemas.recorda import RecordaAuthor


def get_monthly_calendar(
    db: Session, user_id: UUID, year: int, month: int
) -> MonthlyCalendarResponse:
    """Agrupa as Recordas vivas do mês pelo dia local em America/Sao_Paulo.

    Exclusões pelo autor e pela moderação não aparecem.
    """
    start, end = local_month_bounds(year, month)
    recordas_by_day: dict[date, list[Recorda]] = defaultdict(list)
    for recorda in recorda_repository.list_by_user_between(db, user_id, start, end):
        recordas_by_day[_local_day(recorda.created_at)].append(recorda)

    days = [
        CalendarDaySummary(
            date=day,
            day=day.day,
            count=len(recordas),
            thumbnail_url=recordas[0].media_url,
            media_type=recordas[0].media_type,
            first_recorda_id=recordas[0].recorda_id,
            song_cover_url=recordas[0].song_cover_url,
        )
        for day, recordas in sorted(recordas_by_day.items())
    ]
    return MonthlyCalendarResponse(
        year=year,
        month=month,
        total_memories=sum(day.count for day in days),
        active_days_count=len(days),
        days=days,
    )


def _local_day(value: datetime) -> date:
    """O SQLite dos testes devolve datetime sem fuso; o valor gravado é UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return to_local(value).date()


def get_daily_memories(
    db: Session, user_id: UUID, target_date: date, viewer_id: UUID | None = None
) -> DailyMemoriesResponse:
    """Memórias vivas do dia local e navegação entre dias com publicações."""
    viewer_id = viewer_id or user_id
    start, end = local_day_bounds(target_date)
    recordas = recorda_repository.list_by_user_between(db, user_id, start, end)
    previous_time, next_time = recorda_repository.adjacent_publication_times(
        db, user_id, start, end
    )
    memories = []
    if recordas:
        recorda_ids = [recorda.recorda_id for recorda in recordas]
        likes = recorda_like_repository.summarize_for_recordas(
            db, recorda_ids, viewer_id
        )
        comments = comment_repository.count_visible_for_recordas(db, recorda_ids)
        author = user_repository.get_by_id(db, user_id)
        recorda_author = RecordaAuthor(
            user_id=author.user_id,
            username=author.username,
            avatar_url=author.profile_picture_url,
        )
        for recorda in recordas:
            likes_count, is_liked = likes.get(recorda.recorda_id, (0, False))
            created_at = recorda.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            memories.append(
                DayRecordaDetail(
                    recorda_id=recorda.recorda_id,
                    author=recorda_author,
                    media_url=recorda.media_url,
                    media_type=recorda.media_type,
                    description=recorda.description,
                    deezer_track_id=recorda.deezer_track_id,
                    song_title=recorda.song_title,
                    song_artist_name=recorda.song_artist_name,
                    song_cover_url=recorda.song_cover_url,
                    song_preview_url=public_preview_url(
                        recorda.deezer_track_id, recorda.song_preview_url
                    ),
                    song_genre_name=recorda.song_genre_name,
                    created_at=created_at,
                    formatted_time=to_local(created_at).strftime("%H:%M"),
                    likes_count=likes_count,
                    is_liked=is_liked,
                    comments_count=comments.get(recorda.recorda_id, 0),
                )
            )
    return DailyMemoriesResponse(
        date=target_date,
        total_count=len(memories),
        memories=memories,
        previous_date_with_memories=(
            _local_day(previous_time) if previous_time is not None else None
        ),
        next_date_with_memories=_local_day(next_time)
        if next_time is not None
        else None,
    )
