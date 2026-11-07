"""Strategy engine with a profile bundle and reusable independent calculators."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import local_day_bounds, now_utc, to_local
from app.repositories import metrics_repository
from app.schemas.metrics import DailyStreakMetric, MetricsPeriod, ProfileMetricsResponse
from app.services.metrics.calculators.engagement import EngagementCalculator
from app.services.metrics.calculators.streak import StreakCalculator
from app.services.metrics.calculators.tagged_users import TaggedUsersCalculator
from app.services.metrics.calculators.top_artists import TopArtistsCalculator
from app.services.metrics.calculators.top_genres import TopGenresCalculator
from app.services.metrics.calculators.total_recordas import TotalRecordasCalculator
from app.services.metrics.context import MetricCalculator, MetricsContext


def local_publication_day(value: datetime):
    return to_local(value if value.tzinfo else value.replace(tzinfo=UTC)).date()


class MetricsEngine:
    def __init__(self, calculators: dict[str, MetricCalculator] | None = None):
        self.calculators = {
            "top_artists": TopArtistsCalculator(),
            "top_genres": TopGenresCalculator(),
            "streak": StreakCalculator(),
            "total_recordas": TotalRecordasCalculator(),
            "tagged_users": TaggedUsersCalculator(),
            "engagement": EngagementCalculator(),
        }
        if calculators:
            self.calculators.update(calculators)

    def calculate(self, name: str, context: MetricsContext):
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
        days = frozenset(
            local_publication_day(t)
            for t in metrics_repository.list_publication_times(db, user_id, now)
        )
        context = MetricsContext(recordas, days, today)
        artists = self.calculate("top_artists", context)
        streak = self.calculate("streak", context)
        return ProfileMetricsResponse(
            period=period,
            top_artist=artists[0] if artists else None,
            top_genres=self.calculate("top_genres", context),
            streak=DailyStreakMetric(
                current_streak_days=streak.current_streak,
                last_post_date=streak.last_post_date,
            ),
        )
