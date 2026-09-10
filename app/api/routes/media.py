from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.repositories import media_storage_repository
from app.schemas.media import MediaUploadResponse
from app.services import media_service

router = APIRouter(prefix="/recordas", tags=["recordas"])


@router.post(
    "/media", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    current_user: Annotated[User, Depends(get_current_user)],
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> Response:
    media = media_storage_repository.get_by_filename(db, filename)

    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada"
        )

    return Response(content=media.content, media_type=media.content_type)
