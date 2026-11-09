from collections import Counter

from app.core.time import to_local
from app.schemas.metrics import MonthlyCountMetric
from app.services.metrics.context import MetricsContext


class MonthlyDistributionCalculator:
    def calculate(self, context: MetricsContext) -> list[MonthlyCountMetric]:
        counts = Counter(
            (local.year, local.month)
            for local in (to_local(r.created_at) for r in context.recordas)
        )
        return [
            MonthlyCountMetric(year=year, month=month, count=count)
            for (year, month), count in sorted(counts.items())
        ]
