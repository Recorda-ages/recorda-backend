import uuid

from pydantic import BaseModel, ConfigDict, Field


class CalendarDaySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str = Field(description="Data da publicação no formato YYYY-MM-DD")
    day: int = Field(ge=1, le=31, description="Dia do mês (1-31)")
    count: int = Field(ge=1, description="Total de memórias publicadas no dia")
    thumbnail_url: str = Field(description="Miniatura da primeira memória do dia")
    media_type: str = Field(description="Tipo de mídia: 'PHOTO' ou 'VIDEO'")
    first_recorda_id: uuid.UUID = Field(description="ID da primeira Recorda do dia")


class MonthlyCalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int = Field(description="Ano consultado")
    month: int = Field(ge=1, le=12, description="Mês consultado")
    total_memories: int = Field(description="Total acumulado de memórias no mês")
    active_days_count: int = Field(
        description="Quantidade de dias com publicações ativas"
    )
    days: list[CalendarDaySummary] = Field(
        default_factory=list, description="Lista de dias com memórias"
    )
