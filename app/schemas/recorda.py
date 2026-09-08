from pydantic import BaseModel, ConfigDict, Field


class RecordaCreate(BaseModel):
    midia: str = Field(..., min_length=1)
    music: str = Field(..., min_length=1)
    description: str | None = Field(None, max_length=2200)
    data: str | None = None


class RecordaUpdate(BaseModel):
    midia: str | None = None
    music: str | None = None
    description: str | None = None
    data: str | None = None


class RecordaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    midia: str | None
    music: str | None
    description: str | None
    data: str | None
