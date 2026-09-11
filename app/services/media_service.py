import uuid

from sqlalchemy.orm import Session

from app.core.media_validation import detect_content_type, is_size_allowed
from app.repositories import media_storage_repository
from app.schemas.media import MediaUploadResponse

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "video/mp4": "mp4",
}


class UnsupportedMediaTypeError(Exception):
    pass


class MediaTooLargeError(Exception):
    pass


class MediaStorageError(Exception):
    pass


def upload_media(db: Session, content: bytes) -> MediaUploadResponse:
    content_type = detect_content_type(content[:16])

    if content_type is None:
        raise UnsupportedMediaTypeError()

    if not is_size_allowed(len(content)):
        raise MediaTooLargeError()

    filename = f"{uuid.uuid4()}.{_EXTENSIONS[content_type]}"

    try:
        media_storage_repository.save(db, filename, content, content_type)
    except Exception as exc:
        raise MediaStorageError() from exc

    return MediaUploadResponse(
        url=f"/api/v1/recordas/media/{filename}",
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
    )
