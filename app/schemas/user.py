from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import (
    MINIMUM_PASSWORD_LENGTH,
    validate_email,
    validate_name,
    validate_username,
)
from app.schemas.profile import FollowStatus
from app.schemas.profile import ProfileFavoriteSong as ProfileFavoriteSong
from app.schemas.recorda import RecordaRead


class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    username: str
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserChangeRole(BaseModel):
    role: Literal["USER", "ADMIN"]


class AccountRead(BaseModel):
    """Dados editáveis da tela "Minha conta" (US34)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    name: str
    username: str
    email: str


class AccountUpdate(BaseModel):
    """Atualização parcial da conta: campo omitido ou nulo fica inalterado.

    A senha nova não exige a atual; a confirmação do par é feita na tela.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=MINIMUM_PASSWORD_LENGTH)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        return None if value is None else validate_name(value)

    @field_validator("username")
    @classmethod
    def username_must_not_have_spaces(cls, value: str | None) -> str | None:
        return None if value is None else validate_username(value)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str | None) -> str | None:
        return None if value is None else validate_email(value)


class AccountUpdateResponse(BaseModel):
    """O token é reemitido porque trocar o username invalida o anterior."""

    access_token: str
    token_type: str = "bearer"
    account: AccountRead


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    role: str


class UserSearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    avatar_url: str | None
    follow_status: FollowStatus


class SuggestedUser(BaseModel):
    """Perfil sugerido por afinidade musical (US27).

    Sem `follow_status`: a sugestão exclui quem já é seguido e quem tem
    solicitação pendente, então a relação é sempre inexistente.
    """

    user_id: UUID
    username: str
    avatar_url: str | None
    affinity: float
    common_genres: list[str]
    common_artists: list[str]


class ProfileGenre(BaseModel):
    genre_id: UUID
    name: str


class ProfileArtist(BaseModel):
    deezer_artist_id: str
    name: str
    image_url: str | None


class UserProfileRead(BaseModel):
    user_id: UUID
    username: str
    name: str
    profile_picture_url: str | None
    favorite_song: ProfileFavoriteSong
    favorite_genres: list[ProfileGenre]
    favorite_artists: list[ProfileArtist]
    recordas: list[RecordaRead]
