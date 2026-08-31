from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    username: str
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserChangeAccountType(BaseModel):
    account_type: Literal["common", "admin"]


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
