import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MINIMUM_PASSWORD_LENGTH = 8

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    return value.strip().lower()


class LoginRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def strip_username(cls, value: str) -> str:
        return value.strip()


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MINIMUM_PASSWORD_LENGTH)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Informe seu nome.")
        return stripped

    @field_validator("username")
    @classmethod
    def username_must_not_have_spaces(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Informe seu usuário.")
        if re.search(r"\s", stripped):
            raise ValueError("O usuário não pode conter espaços.")
        return stripped

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        normalized = normalize_email(value)
        if not _EMAIL_PATTERN.match(normalized):
            raise ValueError("Informe um email válido.")
        return normalized


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str = Field(..., min_length=MINIMUM_PASSWORD_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return normalize_email(value)


class ResetPasswordResponse(BaseModel):
    message: str = "Senha redefinida com sucesso"


class UserBasicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    name: str
    username: str
    role: str
    onboarding_completed: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBasicResponse
