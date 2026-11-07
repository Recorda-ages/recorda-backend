from collections import Counter

from app.schemas.metrics import TopArtistMetric
from app.services.metrics.context import MetricsContext


class TopArtistsCalculator:
    def calculate(self, context: MetricsContext) -> list[TopArtistMetric]:
        counts = Counter(r.song_artist_name for r in context.recordas)
        # Deterministic tie break by artist name; latest available cover per artist.
        covers = {}
        for recorda in context.recordas:
            covers[recorda.song_artist_name] = recorda.song_cover_url
        return [
            TopArtistMetric(
                artist_name=name, memory_count=count, image_url=covers[name]
            )
            for name, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]
