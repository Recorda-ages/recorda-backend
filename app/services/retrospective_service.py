from collections import Counter
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.music_preview import public_preview_url
from app.core.time import local_month_bounds, local_year_bounds, now_utc, to_local
from app.models import Recorda
from app.repositories import recorda_repository, retrospective_repository
from app.schemas.metrics import RecordaMetrics
from app.schemas.retrospectives import (
    AvailablePeriod,
    AvailablePeriodsResponse,
    RetrospectiveDetailsResponse,
    RetrospectiveEngagement,
    RetrospectiveFeaturedSong,
    RetrospectivePeriodQuery,
)
from app.services.metrics.context import MetricsContext
from app.services.metrics.engine import MetricsEngine, local_publication_day


def get_available_periods(db: Session, user_id: UUID) -> AvailablePeriodsResponse:

    recorda_dates = retrospective_repository.search_retrospectives(db, user_id)

    recorda_dates = [ensure_utc(date) for date in recorda_dates]

    recorda_dates_local = [to_local(date) for date in recorda_dates]

    if not recorda_dates_local:
        return AvailablePeriodsResponse(periods=[])

    current_utc = now_utc()

    current_sp = to_local(current_utc)

    current_year = current_sp.year
    current_month = current_sp.month

    monthly_counts: dict[tuple[int, int], int] = {}

    for recorda_date in recorda_dates_local:
        period_key = (recorda_date.year, recorda_date.month)
        monthly_counts[period_key] = monthly_counts.get(period_key, 0) + 1

    yearly_counts: dict[int, int] = {}

    for recorda_date in recorda_dates_local:
        period_key = recorda_date.year
        yearly_counts[period_key] = yearly_counts.get(period_key, 0) + 1

    available_periods = []

    month_names = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    for (year, month), count in monthly_counts.items():
        if (year, month) > (current_year, current_month):
            continue

        is_preview = (year, month) == (current_year, current_month)

        available_periods.append(
            AvailablePeriod(
                period_type="MONTHLY",
                year=year,
                month=month,
                label=f"{month_names[month - 1]} {year}",
                total_memories=count,
                is_preview=is_preview,
            )
        )

    for (year), count in yearly_counts.items():
        if (year) >= (current_year):
            continue

        available_periods.append(
            AvailablePeriod(
                period_type="YEARLY",
                year=year,
                month=None,
                label=f"Ano de {year}",
                total_memories=count,
                is_preview=False,
            )
        )

    available_periods.sort(key=lambda p: (p.year, p.month or 0), reverse=True)

    return AvailablePeriodsResponse(periods=available_periods)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value


# ---------------------------------------------------------------------------
# Detalhes da retrospectiva (T-E7.US39.BE.02)
# ---------------------------------------------------------------------------

TOP_ARTISTS_LIMIT = 5

MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)

_engine = MetricsEngine()


class RetrospectiveNotFoundError(Exception):
    """Período futuro, ano ainda em andamento ou sem Recordas vivas."""


def get_retrospective_details(
    db: Session,
    user_id: UUID,
    query: RetrospectivePeriodQuery,
    *,
    now: datetime | None = None,
) -> RetrospectiveDetailsResponse:
    today = local_publication_day(now or now_utc())
    is_preview = _check_period_is_available(query, today)
    start, end = _period_bounds(query)

    recordas = recorda_repository.list_by_user_between(db, user_id, start, end)
    if not recordas:
        raise RetrospectiveNotFoundError

    context = MetricsContext(
        recordas=tuple(_to_metrics(recorda) for recorda in recordas),
        publication_days=frozenset(
            local_publication_day(recorda.created_at) for recorda in recordas
        ),
        today=today,
        likes=retrospective_repository.count_likes_received(db, user_id, start, end),
        comments=retrospective_repository.count_comments_received(
            db, user_id, start, end
        ),
    )
    return _build_details(query, is_preview, recordas, context)


def _check_period_is_available(query: RetrospectivePeriodQuery, today: date) -> bool:
    """Mesma regra da lista de períodos (#148). Devolve se o período é prévia."""
    if query.month is None:
        if query.year >= today.year:
            raise RetrospectiveNotFoundError
        return False

    requested = (query.year, query.month)
    current = (today.year, today.month)
    if requested > current:
        raise RetrospectiveNotFoundError
    return requested == current


def _period_bounds(query: RetrospectivePeriodQuery) -> tuple[datetime, datetime]:
    # month é None só em YEARLY (garantido por RetrospectivePeriodQuery).
    if query.month is None:
        return local_year_bounds(query.year)
    return local_month_bounds(query.year, query.month)


def _period_label(query: RetrospectivePeriodQuery) -> str:
    if query.month is None:
        return f"Ano de {query.year}"
    return f"{MONTH_NAMES[query.month - 1]} {query.year}"


def _to_metrics(recorda: Recorda) -> RecordaMetrics:
    return RecordaMetrics(
        recorda_id=recorda.recorda_id,
        created_at=recorda.created_at,
        song_artist_name=recorda.song_artist_name,
        song_cover_url=recorda.song_cover_url,
        song_genre_name=recorda.song_genre_name,
    )


def _featured_song(recordas: list[Recorda]) -> RetrospectiveFeaturedSong:
    """Faixa mais repetida; no empate, a que apareceu primeiro no período."""
    # most_common mantém a ordem de primeira ocorrência entre empatados,
    # e as Recordas chegam em ordem cronológica.
    track_id, memory_count = Counter(r.deezer_track_id for r in recordas).most_common(
        1
    )[0]
    first = next(r for r in recordas if r.deezer_track_id == track_id)
    return RetrospectiveFeaturedSong(
        deezer_track_id=track_id,
        song_title=first.song_title,
        song_artist_name=first.song_artist_name,
        song_cover_url=first.song_cover_url or None,
        song_preview_url=public_preview_url(track_id, first.song_preview_url),
        memory_count=memory_count,
    )


def _build_details(
    query: RetrospectivePeriodQuery,
    is_preview: bool,
    recordas: list[Recorda],
    context: MetricsContext,
) -> RetrospectiveDetailsResponse:
    engagement = _engine.calculate("engagement", context)
    return RetrospectiveDetailsResponse(
        period_type=query.period_type,
        year=query.year,
        month=query.month,
        label=_period_label(query),
        is_preview=is_preview,
        total_recordas=_engine.calculate("total_recordas", context),
        active_days=len(context.publication_days),
        top_artists=_engine.calculate("top_artists", context)[:TOP_ARTISTS_LIMIT],
        top_genres=_engine.calculate("top_genres", context),
        # Sem fonte de marcações até a recorda_mention existir (issue #17).
        tagged_users=[],
        engagement=RetrospectiveEngagement(
            likes_received=engagement.likes,
            comments_received=engagement.comments,
        ),
        max_streak=_engine.calculate("streak", context).max_streak,
        featured_song=_featured_song(recordas),
    )
