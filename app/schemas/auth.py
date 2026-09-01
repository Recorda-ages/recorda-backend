from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class UserBasicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    account_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBasicResponse
