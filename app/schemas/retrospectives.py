from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.metrics import TopArtistMetric, TopGenreMetric

PeriodType = Literal["MONTHLY", "YEARLY"]


class AvailablePeriod(BaseModel):
    period_type: PeriodType
    year: int = Field(ge=1, le=9999)
    month: int | None = Field(ge=1, le=12)
    label: str
    total_memories: int = Field(ge=1)
    is_preview: bool

    @model_validator(mode="after")
    def validate_period(self) -> "AvailablePeriod":
        if self.period_type == "MONTHLY" and self.month is None:
            raise ValueError("Períodos mensais precisam informar o mês")
        if self.period_type == "YEARLY" and (self.month is not None or self.is_preview):
            raise ValueError("Períodos anuais não têm mês nem prévia")
        return self


class AvailablePeriodsResponse(BaseModel):
    periods: list[AvailablePeriod]


class RetrospectivePeriodQuery(BaseModel):
    """Parâmetros de GET /users/me/retrospectives."""

    period_type: PeriodType
    year: int = Field(ge=1, le=9999)
    month: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def validate_month(self) -> "RetrospectivePeriodQuery":
        if self.period_type == "MONTHLY" and self.month is None:
            raise ValueError("Retrospectivas mensais precisam informar o mês")
        if self.period_type == "YEARLY" and self.month is not None:
            raise ValueError("Retrospectivas anuais não têm mês")
        return self


class RetrospectiveTaggedUser(BaseModel):
    user_id: UUID
    username: str
    profile_picture_url: str | None
    tag_count: int = Field(ge=1)


class RetrospectiveEngagement(BaseModel):
    likes_received: int = Field(ge=0)
    comments_received: int = Field(ge=0)


class RetrospectiveFeaturedSong(BaseModel):
    deezer_track_id: str
    song_title: str
    song_artist_name: str
    song_cover_url: str | None
    song_preview_url: str | None
    memory_count: int = Field(ge=1)


class RetrospectiveDetailsResponse(BaseModel):
    period_type: PeriodType
    year: int = Field(ge=1, le=9999)
    month: int | None = Field(ge=1, le=12)
    label: str
    is_preview: bool
    total_recordas: int = Field(ge=1)
    active_days: int = Field(ge=1)
    top_artists: list[TopArtistMetric] = Field(max_length=5)
    top_genres: list[TopGenreMetric]
    tagged_users: list[RetrospectiveTaggedUser]
    engagement: RetrospectiveEngagement
    max_streak: int = Field(ge=1)
    featured_song: RetrospectiveFeaturedSong | None
