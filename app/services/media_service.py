import uuid

from sqlalchemy.orm import Session

from app.core.media_validation import detect_content_type, is_size_allowed
from app.core.mp4_faststart import move_moov_to_front
from app.models import AppUser
from app.models.app_user import ROLE_ADMIN
from app.repositories import media_storage_repository, recorda_repository
from app.schemas.media import MediaUploadResponse
from app.services import recorda_service

MEDIA_URL_PREFIX = "/api/v1/recordas/media/"

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


class MediaNotFoundError(Exception):
    """Mídia publicada que o usuário não pode ver; a rota responde como inexistente."""


def upload_media(db: Session, content: bytes) -> MediaUploadResponse:
    content_type = detect_content_type(content[:16])

    if content_type is None:
        raise UnsupportedMediaTypeError()

    if not is_size_allowed(len(content)):
        raise MediaTooLargeError()

    if content_type == "video/mp4":
        content = move_moov_to_front(content)

    filename = f"{uuid.uuid4()}.{_EXTENSIONS[content_type]}"

    try:
        media_storage_repository.save(db, filename, content, content_type)
    except Exception as exc:
        raise MediaStorageError() from exc

    return MediaUploadResponse(
        url=f"{MEDIA_URL_PREFIX}{filename}",
        filename=filename,
        content_type=content_type,
        size_bytes=len(content),
    )


def ensure_published_media_visible(db: Session, filename: str, viewer: AppUser) -> None:
    """Libera a mídia se ao menos uma Recorda que a usa for visível para `viewer`.

    Mídia sem Recorda é prévia de upload e continua liberada: a tabela Media
    não tem dono. ADMIN vê tudo, para investigar denúncias.
    """
    if viewer.role == ROLE_ADMIN:
        return
    recordas = recorda_repository.list_by_media_url(db, f"{MEDIA_URL_PREFIX}{filename}")
    if not recordas:
        return

    for recorda in recordas:
        try:
            if recorda_service.get_viewable_recorda(db, recorda.recorda_id, viewer):
                return
        except recorda_service.RecordaAccessDeniedError:
            continue
    raise MediaNotFoundError()
