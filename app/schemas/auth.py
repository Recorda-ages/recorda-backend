from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str = Field(..., min_length=8)


class ResetPasswordResponse(BaseModel):
    message: str = "Senha redefinida com sucesso"


class UserBasicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    account_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBasicResponse
