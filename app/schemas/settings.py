from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserSettings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_private: bool
    language: str


class UserSettingsUpdate(BaseModel):
    is_private: bool | None = None
    language: Literal["pt-BR", "en", "es"] | None = None


class UserSettingsResult(UserSettings):
    accepted_requests: int
