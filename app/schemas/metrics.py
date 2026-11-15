"""Contracts for the profile metrics bundle."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MetricsPeriod(StrEnum):
    ALL_TIME = "all_time"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_YEAR = "last_year"


class TopArtistMetric(BaseModel):
    artist_name: str
    memory_count: int = Field(ge=0)
    image_url: str | None


class TopGenreMetric(BaseModel):
    genre_name: str
    count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class DailyStreakMetric(BaseModel):
    current_streak_days: int = Field(ge=0)
    last_post_date: date | None


class MonthlyCountMetric(BaseModel):
    year: int = Field(ge=1, le=9999)
    month: int = Field(ge=1, le=12)
    count: int = Field(ge=1)


class ProfileMetricsResponse(BaseModel):
    period: MetricsPeriod
    total_recordas: int = Field(ge=0)
    top_artist: TopArtistMetric | None
    top_artists: list[TopArtistMetric] = Field(max_length=5)
    top_genres: list[TopGenreMetric]
    monthly_distribution: list[MonthlyCountMetric]
    streak: DailyStreakMetric


@dataclass(frozen=True)
class RecordaMetrics:
    """Publication snapshot containing only fields used by calculators."""

    recorda_id: UUID
    created_at: datetime
    song_artist_name: str
    song_cover_url: str
    song_genre_name: str | None

    def __post_init__(self) -> None:
        # SQLite returns naive UTC timestamps; PostgreSQL returns aware ones.
        timestamp = self.created_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        object.__setattr__(self, "created_at", timestamp.astimezone(UTC))
