from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recorda import RecordaCreate, RecordaRead, RecordaUpdate
from app.services import recorda_service, recorda_service

router = APIRouter(prefix="/recordas", tags=["recordas"])

@router.get("", response_model=list[RecordaRead])
def list_recordas(db: Session = Depends(get_db)) -> list[RecordaRead]:
    return recorda_service.get_all(db)

@router.post("", response_model=RecordaRead, status_code=status.HTTP_201_CREATED)
def create_recorda(payload: RecordaCreate, db: Session = Depends(get_db)) -> RecordaRead:
    return recorda_service.create(db, payload)