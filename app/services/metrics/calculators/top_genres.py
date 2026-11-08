from collections import Counter

from app.schemas.metrics import TopGenreMetric
from app.services.metrics.context import MetricsContext


class TopGenresCalculator:
    def calculate(self, context: MetricsContext) -> list[TopGenreMetric]:
        counts = Counter(
            r.song_genre_name for r in context.recordas if r.song_genre_name
        )
        total = len(context.recordas)
        return [
            TopGenreMetric(
                genre_name=name, count=count, percentage=round(count * 100 / total, 2)
            )
            for name, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]
