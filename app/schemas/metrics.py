"""Contracts for the profile metrics bundle."""

from datetime import date
from enum import StrEnum

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


class ProfileMetricsResponse(BaseModel):
    period: MetricsPeriod
    top_artist: TopArtistMetric | None
    top_genres: list[TopGenreMetric]
    streak: DailyStreakMetric
