"""Shared immutable input; calculators do not access the database or clock."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.models import Recorda


@dataclass(frozen=True)
class MetricsContext:
    recordas: tuple[Recorda, ...]
    publication_days: frozenset[date]
    today: date
    # Retrospective callers supply explicit tag relations and engagement counts.
    tagged_user_ids: tuple[UUID, ...] = ()
    likes: int = 0
    comments: int = 0


class MetricCalculator[T](Protocol):
    def calculate(self, context: MetricsContext) -> T: ...
