"""Contrato do calendário mensal de memórias: GET /users/me/calendar (US37)."""

import datetime as dt
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.recorda import MediaType


class CalendarDaySummary(BaseModel):
    """Dia do mês com ao menos uma Recorda viva; a miniatura é a primeira do dia."""

    date: dt.date = Field(description="Dia local em America/Sao_Paulo (YYYY-MM-DD)")
    day: int = Field(ge=1, le=31, description="Dia do mês (1-31)")
    count: int = Field(ge=1, description="Recordas publicadas no dia")
    thumbnail_url: str = Field(description="`media_url` da primeira Recorda do dia")
    media_type: MediaType = Field(description="Tipo de mídia da primeira Recorda")
    first_recorda_id: UUID = Field(description="ID da primeira Recorda do dia")


class MonthlyCalendarResponse(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    total_memories: int = Field(ge=0, description="Recordas vivas no mês")
    active_days_count: int = Field(ge=0, description="Dias com publicações")
    days: list[CalendarDaySummary] = Field(
        description="Somente dias com publicações, em ordem crescente"
    )
