"""Contratos do calendário mensal e do detalhe diário de memórias (US37)."""

import datetime as dt
import re
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas.recorda import MediaType, RecordaDetail


def _parse_calendar_date(value: object) -> dt.date:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Informe a data no formato YYYY-MM-DD")
    try:
        day = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Informe uma data válida") from exc
    if day == dt.date.max:
        raise ValueError("A data deve permitir o cálculo do início do dia seguinte")
    return day


CalendarDate = Annotated[dt.date, BeforeValidator(_parse_calendar_date)]


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


class DayRecordaDetail(RecordaDetail):
    """Detalhe de uma memória do dia, com engajamento e horário local."""

    comments_count: int = Field(ge=0, description="Comentários visíveis na Recorda")
    formatted_time: str = Field(
        pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$",
        description="Horário da publicação em America/Sao_Paulo (HH:MM)",
    )


class DailyMemoriesResponse(BaseModel):
    date: dt.date = Field(description="Dia local em America/Sao_Paulo (YYYY-MM-DD)")
    total_count: int = Field(ge=0, description="Recordas vivas no dia")
    memories: list[DayRecordaDetail] = Field(
        description="Memórias em ordem cronológica crescente"
    )
    previous_date_with_memories: dt.date | None = Field(
        description="Dia anterior mais próximo com memórias, ou null"
    )
    next_date_with_memories: dt.date | None = Field(
        description="Dia posterior mais próximo com memórias, ou null"
    )
