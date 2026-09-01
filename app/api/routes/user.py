from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.db.session import get_db
from app.schemas.user import UserChangeAccountType, UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

_current_admin = Depends(get_current_admin_user)


@router.get("", response_model=list[UserRead], dependencies=[_current_admin])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return user_service.get_all(db)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    return user_service.create(db, payload)


@router.get("/{user_id}", response_model=UserRead, dependencies=[_current_admin])
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead, dependencies=[_current_admin])
def update_user(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db)
) -> UserRead:
    user = user_service.update(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_current_admin]
)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    if not user_service.delete(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")


@router.patch(
    "/{user_id}/account-type",
    response_model=UserRead,
    dependencies=[_current_admin],
)
def change_account_type(
    user_id: int,
    payload: UserChangeAccountType,
    db: Session = Depends(get_db),
) -> UserRead:
    user = user_service.change_account_type(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
