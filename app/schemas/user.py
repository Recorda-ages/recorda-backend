from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
