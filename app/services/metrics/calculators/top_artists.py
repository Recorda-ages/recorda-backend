from collections import Counter

from app.schemas.metrics import RecordaMetrics, TopArtistMetric
from app.services.metrics.context import MetricsContext


class TopArtistsCalculator:
    def calculate(self, context: MetricsContext) -> list[TopArtistMetric]:
        counts = Counter(r.song_artist_name for r in context.recordas)
        # Deterministic ranking and cover selection, independent of input order.
        latest: dict[str, RecordaMetrics] = {}
        for recorda in context.recordas:
            previous = latest.get(recorda.song_artist_name)
            if previous is None or (recorda.created_at, recorda.recorda_id) > (
                previous.created_at,
                previous.recorda_id,
            ):
                latest[recorda.song_artist_name] = recorda
        return [
            TopArtistMetric(
                artist_name=name,
                memory_count=count,
                image_url=latest[name].song_cover_url,
            )
            for name, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]
