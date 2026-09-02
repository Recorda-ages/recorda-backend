from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recorda import RecordaCreate, RecordaRead
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


@router.delete("/{recorda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recorda(recorda_id: int, db: Session = Depends(get_db)) -> None:
    if not recorda_service.delete(db, recorda_id):
        raise HTTPException(status_code=404, detail="Recorda not found")
