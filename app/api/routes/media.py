import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.repositories import media_storage_repository
from app.schemas.media import MediaUploadResponse
from app.services import media_service

router = APIRouter(prefix="/recordas", tags=["recordas"])

_SINGLE_BYTE_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


class _UnsatisfiableRange(Exception):
    pass


def _parse_byte_range(header: str, size: int) -> tuple[int, int] | None:
    """Returns the inclusive (start, end) to serve, or None to serve the whole file.

    Malformed and multi-range headers fall back to a full 200 response, which RFC 9110
    allows; only a well-formed range outside the file is rejected.
    """
    match = _SINGLE_BYTE_RANGE.match(header.strip())
    if match is None:
        return None
    first, last = match.groups()
    if not first and not last:
        return None

    if not first:
        suffix_length = int(last)
        if suffix_length == 0:
            raise _UnsatisfiableRange
        return max(size - suffix_length, 0), size - 1

    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or start > end:
        raise _UnsatisfiableRange
    return start, end


@router.post(
    "/media", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    current_user: Annotated[AppUser, Depends(get_current_user)],
    file: UploadFile,
    db: Session = Depends(get_db),
) -> MediaUploadResponse:
    content = await file.read()

    try:
        return media_service.upload_media(db, content)
    except media_service.UnsupportedMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo não suportado",
        ) from exc
    except media_service.MediaTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Arquivo excede o tamanho máximo permitido",
        ) from exc
    except media_service.MediaStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao armazenar a mídia. Tente novamente.",
        ) from exc


@router.get("/media/{filename}")
def get_media(
    filename: str,
    current_user: Annotated[AppUser, Depends(get_current_user)],
    db: Session = Depends(get_db),
    range_header: Annotated[str | None, Header(alias="Range")] = None,
) -> Response:
    info = media_storage_repository.get_info(db, filename)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada"
        )

    # iOS AVPlayer only plays video from servers that answer byte-range requests.
    content_type, size = info
    headers = {"Accept-Ranges": "bytes"}

    try:
        byte_range = _parse_byte_range(range_header, size) if range_header else None
    except _UnsatisfiableRange:
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={**headers, "Content-Range": f"bytes */{size}"},
        )

    if byte_range is None:
        media = media_storage_repository.get_by_filename(db, filename)
        return Response(content=media.content, media_type=content_type, headers=headers)

    start, end = byte_range
    return Response(
        content=media_storage_repository.get_bytes(db, filename, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=content_type,
        headers={**headers, "Content-Range": f"bytes {start}-{end}/{size}"},
    )
