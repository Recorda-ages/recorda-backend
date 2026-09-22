from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    url: str
    filename: str
    content_type: str
    size_bytes: int
