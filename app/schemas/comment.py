from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O comentário não pode estar vazio.")
        return value


class CommentRead(BaseModel):
    comment_id: UUID
    user_id: UUID
    username: str
    avatar_url: str | None
    content: str
    created_at: datetime
