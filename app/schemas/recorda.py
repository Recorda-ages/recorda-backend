from pydantic import BaseModel, ConfigDict


class RecordaBase(BaseModel):
    midia: str
    musica: str
    descricao: str
    data: str


class RecordaCreate(RecordaBase):
    midia: str | None = None
    musica: str | None = None
    descricao: str | None = None
    data: str | None = None


class RecordaUpdate(BaseModel):
    midia: str | None = None
    musica: str | None = None
    descricao: str | None = None
    data: str | None = None


class RecordaRead(RecordaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
