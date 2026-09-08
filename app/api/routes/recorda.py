from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recorda import RecordaCreate, RecordaRead, RecordaUpdate
from app.services import recorda_service

router = APIRouter(prefix="/recordas", tags=["recordas"])


@router.get("", response_model=list[RecordaRead])
def list_recordas(db: Session = Depends(get_db)) -> list[RecordaRead]:
    return recorda_service.get_all(db)


@router.post("", response_model=RecordaRead, status_code=status.HTTP_201_CREATED)
def create_recorda(
    payload: RecordaCreate, db: Session = Depends(get_db)
) -> RecordaRead:
    return recorda_service.create(db, payload)


@router.get("/{recorda_id}", response_model=RecordaRead)
def get_recorda(recorda_id: int, db: Session = Depends(get_db)) -> RecordaRead:
    recorda = recorda_service.get_by_id(db, recorda_id)
    if recorda is None:
        raise HTTPException(status_code=404, detail="Recorda not found")
    return recorda


@router.put("/{recorda_id}", response_model=RecordaRead)
def update_recorda(
    recorda_id: int, payload: RecordaUpdate, db: Session = Depends(get_db)
) -> RecordaRead:
    recorda = recorda_service.update(db, recorda_id, payload)
    if recorda is None:
        raise HTTPException(status_code=404, detail="Recorda not found")
    return recorda


@router.delete("/{recorda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recorda(recorda_id: int, db: Session = Depends(get_db)) -> None:
    if not recorda_service.delete(db, recorda_id):
        raise HTTPException(status_code=404, detail="Recorda not found")
