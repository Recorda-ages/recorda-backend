from dataclasses import dataclass

from app.services.metrics.context import MetricsContext


@dataclass(frozen=True)
class EngagementResult:
    likes: int
    comments: int
    total: int


class EngagementCalculator:
    def calculate(self, context: MetricsContext) -> EngagementResult:
        return EngagementResult(
            context.likes, context.comments, context.likes + context.comments
        )
