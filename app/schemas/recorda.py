from pydantic import BaseModel, ConfigDict


class RecordaBase(BaseModel):
    midia: str
    music: str
    description: str
    data: str


class RecordaCreate(RecordaBase):
    midia: str | None = None
    music: str | None = None
    description: str | None = None
    data: str | None = None


class RecordaUpdate(BaseModel):
    midia: str | None = None
    music: str | None = None
    description: str | None = None
    data: str | None = None


class RecordaRead(RecordaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
