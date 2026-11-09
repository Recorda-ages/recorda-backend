"""Strategy engine with a profile bundle and reusable independent calculators."""

from datetime import UTC, date, datetime, timedelta
from typing import Literal, TypedDict, overload
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import local_day_bounds, now_utc, to_local
from app.repositories import metrics_repository
from app.schemas.metrics import (
    DailyStreakMetric,
    MetricsPeriod,
    MonthlyCountMetric,
    ProfileMetricsResponse,
    TopArtistMetric,
    TopGenreMetric,
)
from app.services.metrics.calculators.engagement import (
    EngagementCalculator,
    EngagementResult,
)
from app.services.metrics.calculators.monthly_distribution import (
    MonthlyDistributionCalculator,
)
from app.services.metrics.calculators.streak import StreakCalculator, StreakResult
from app.services.metrics.calculators.tagged_users import TaggedUsersCalculator
from app.services.metrics.calculators.top_artists import TopArtistsCalculator
from app.services.metrics.calculators.top_genres import TopGenresCalculator
from app.services.metrics.calculators.total_recordas import TotalRecordasCalculator
from app.services.metrics.context import MetricCalculator, MetricsContext

PROFILE_TOP_ARTISTS_LIMIT = 5


def local_publication_day(value: datetime) -> date:
    return to_local(value if value.tzinfo else value.replace(tzinfo=UTC)).date()


class MetricsCalculators(TypedDict, total=False):
    """Each strategy name has a specific result contract, including overrides."""

    top_artists: MetricCalculator[list[TopArtistMetric]]
    top_genres: MetricCalculator[list[TopGenreMetric]]
    streak: MetricCalculator[StreakResult]
    total_recordas: MetricCalculator[int]
    tagged_users: MetricCalculator[dict[UUID, int]]
    engagement: MetricCalculator[EngagementResult]
    monthly_distribution: MetricCalculator[list[MonthlyCountMetric]]


MetricName = Literal[
    "top_artists",
    "top_genres",
    "streak",
    "total_recordas",
    "tagged_users",
    "engagement",
    "monthly_distribution",
]
MetricResult = (
    list[TopArtistMetric]
    | list[TopGenreMetric]
    | StreakResult
    | int
    | dict[UUID, int]
    | EngagementResult
    | list[MonthlyCountMetric]
)


class MetricsEngine:
    def __init__(self, calculators: MetricsCalculators | None = None) -> None:
        self.calculators: MetricsCalculators = {
            "top_artists": TopArtistsCalculator(),
            "top_genres": TopGenresCalculator(),
            "streak": StreakCalculator(),
            "total_recordas": TotalRecordasCalculator(),
            "tagged_users": TaggedUsersCalculator(),
            "engagement": EngagementCalculator(),
            "monthly_distribution": MonthlyDistributionCalculator(),
        }
        if calculators:
            self.calculators.update(calculators)

    @overload
    def calculate(
        self, name: Literal["top_artists"], context: MetricsContext
    ) -> list[TopArtistMetric]: ...

    @overload
    def calculate(
        self, name: Literal["top_genres"], context: MetricsContext
    ) -> list[TopGenreMetric]: ...

    @overload
    def calculate(
        self, name: Literal["streak"], context: MetricsContext
    ) -> StreakResult: ...

    @overload
    def calculate(
        self, name: Literal["total_recordas"], context: MetricsContext
    ) -> int: ...

    @overload
    def calculate(
        self, name: Literal["tagged_users"], context: MetricsContext
    ) -> dict[UUID, int]: ...

    @overload
    def calculate(
        self, name: Literal["engagement"], context: MetricsContext
    ) -> EngagementResult: ...

    @overload
    def calculate(
        self, name: Literal["monthly_distribution"], context: MetricsContext
    ) -> list[MonthlyCountMetric]: ...

    def calculate(self, name: MetricName, context: MetricsContext) -> MetricResult:
        return self.calculators[name].calculate(context)

    def profile(
        self,
        db: Session,
        user_id: UUID,
        period: MetricsPeriod = MetricsPeriod.ALL_TIME,
        *,
        now: datetime | None = None,
    ) -> ProfileMetricsResponse:
        now = now or now_utc()
        today = local_publication_day(now)
        # Rolling civil-day windows include today; last_year is 365 civil days.
        length = {
            MetricsPeriod.LAST_30_DAYS: 30,
            MetricsPeriod.LAST_90_DAYS: 90,
            MetricsPeriod.LAST_YEAR: 365,
        }.get(period)
        start = (
            local_day_bounds(today - timedelta(days=length - 1))[0] if length else None
        )
        recordas = metrics_repository.list_recordas(db, user_id, start, now)
        # all_time already loaded every live timestamp; avoid querying it twice.
        publication_times = (
            (recorda.created_at for recorda in recordas)
            if start is None
            else metrics_repository.iter_publication_times(db, user_id, now)
        )
        days = frozenset(local_publication_day(t) for t in publication_times)
        context = MetricsContext(recordas, days, today)
        artists = self.calculate("top_artists", context)
        streak = self.calculate("streak", context)
        return ProfileMetricsResponse(
            period=period,
            total_recordas=self.calculate("total_recordas", context),
            top_artist=artists[0] if artists else None,
            top_artists=artists[:PROFILE_TOP_ARTISTS_LIMIT],
            top_genres=self.calculate("top_genres", context),
            monthly_distribution=self.calculate("monthly_distribution", context),
            streak=DailyStreakMetric(
                current_streak_days=streak.current_streak,
                last_post_date=streak.last_post_date,
            ),
        )
