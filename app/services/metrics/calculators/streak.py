from dataclasses import dataclass
from datetime import date, timedelta

from app.services.metrics.context import MetricsContext


@dataclass(frozen=True)
class StreakResult:
    current_streak: int
    max_streak: int
    last_post_date: date | None


class StreakCalculator:
    def calculate(self, context: MetricsContext) -> StreakResult:
        days = sorted(day for day in context.publication_days if day <= context.today)
        longest = run = 0
        previous = None
        for day in days:
            run = run + 1 if previous == day - timedelta(days=1) else 1
            longest = max(longest, run)
            previous = day
        current = 0
        day = context.today
        if day not in context.publication_days:
            day -= timedelta(days=1)
        while day in context.publication_days:
            current += 1
            day -= timedelta(days=1)
        return StreakResult(current, longest, days[-1] if days else None)
