from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.recorda import (
    RecordaCreate,
    RecordaDetail,
    RecordaLikeState,
    RecordaRead,
    RecordaUpdate,
)
from app.services import recorda_like_service, recorda_service

router = APIRouter(prefix="/recordas", tags=["recordas"])

_current_user = Depends(get_current_user)

NOT_FOUND_MESSAGE = "Recorda not found"
NOT_OWNER_MESSAGE = "Apenas o autor pode alterar esta Recorda"
ACCESS_DENIED_MESSAGE = "Você não tem permissão para ver esta Recorda"


@router.get("", response_model=list[RecordaRead], dependencies=[_current_user])
def list_recordas(db: Session = Depends(get_db)) -> list[RecordaRead]:
    return recorda_service.get_all(db)


@router.post("", response_model=RecordaRead, status_code=status.HTTP_201_CREATED)
def create_recorda(
    payload: RecordaCreate,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> RecordaRead:
    return recorda_service.create(db, payload, current_user)


@router.get("/{recorda_id}", response_model=RecordaDetail)
def get_recorda(
    recorda_id: UUID,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> RecordaDetail:
    try:
        recorda = recorda_service.get_by_id_for_viewer(db, recorda_id, current_user)
    except recorda_service.RecordaAccessDeniedError as exc:
        raise _access_denied_error() from exc
    if recorda is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    return recorda


@router.post("/{recorda_id}/likes", response_model=RecordaLikeState)
def like_recorda(
    recorda_id: UUID,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> RecordaLikeState:
    result = recorda_like_service.like(
        db,
        recorda_id=recorda_id,
        current_user=current_user,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    return result


@router.delete("/{recorda_id}/likes", response_model=RecordaLikeState)
def unlike_recorda(
    recorda_id: UUID,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> RecordaLikeState:
    result = recorda_like_service.unlike(
        db,
        recorda_id=recorda_id,
        current_user=current_user,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    return result


@router.put("/{recorda_id}", response_model=RecordaRead)
def update_recorda(
    recorda_id: UUID,
    payload: RecordaUpdate,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> RecordaRead:
    try:
        recorda = recorda_service.update(db, recorda_id, payload, current_user)
    except recorda_service.NotRecordaOwnerError as exc:
        raise _not_owner_error() from exc
    if recorda is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    return recorda


@router.delete("/{recorda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recorda(
    recorda_id: UUID,
    current_user: Annotated[AppUser, _current_user],
    db: Session = Depends(get_db),
) -> None:
    try:
        deleted = recorda_service.delete(db, recorda_id, current_user)
    except recorda_service.NotRecordaOwnerError as exc:
        raise _not_owner_error() from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)


def _not_owner_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=NOT_OWNER_MESSAGE
    )


def _access_denied_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=ACCESS_DENIED_MESSAGE
    )