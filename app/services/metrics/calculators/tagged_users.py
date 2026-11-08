"""Counts explicit tag relations supplied by the caller, never inferred from notifications."""

from collections import Counter
from uuid import UUID

from app.services.metrics.context import MetricsContext


class TaggedUsersCalculator:
    def calculate(self, context: MetricsContext) -> dict[UUID, int]:
        return dict(
            sorted(
                Counter(context.tagged_user_ids).items(),
                key=lambda item: (-item[1], str(item[0])),
            )
        )
