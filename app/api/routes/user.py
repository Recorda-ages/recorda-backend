from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exc
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_current_user
from app.api.routes.auth import user_already_exists_error
from app.db.session import get_db
from app.models import AppUser 
from app.schemas.music_preference import (
    MusicPreferencesCreate,
    MusicPreferencesRead,
)
from app.schemas.user import UserChangeRole, UserCreate, UserRead, UserUpdate
from app.services import follow_service, music_preference_service, user_service

router = APIRouter(prefix="/users", tags=["users"])

_current_admin = Depends(get_current_admin_user)


@router.get("", response_model=list[UserRead], dependencies=[_current_admin])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return user_service.get_all(db)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    try:
        return user_service.create(db, payload)
    except user_service.UserAlreadyExistsError as exc:
        raise user_already_exists_error(exc) from exc


@router.get("/{user_id}", response_model=UserRead, dependencies=[_current_admin])
def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserRead:
    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserRead, dependencies=[_current_admin])
def update_user(
    user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db)
) -> UserRead:
    user = user_service.update(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_current_admin]
)
def delete_user(user_id: UUID, db: Session = Depends(get_db)) -> None:
    if not user_service.delete(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")


@router.patch(
    "/{user_id}/role",
    response_model=UserRead,
    dependencies=[_current_admin],
)
def change_role(
    user_id: UUID,
    payload: UserChangeRole,
    db: Session = Depends(get_db),
) -> UserRead:
    user = user_service.change_role(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/me/music-preferences", response_model=MusicPreferencesRead)
def save_music_preferences(
    payload: MusicPreferencesCreate,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MusicPreferencesRead:
    """Persist the onboarding selection of the authenticated user."""
    return music_preference_service.replace_for_user(db, current_user, payload)


@router.post("/{user_id}/follow")
def create_follow(user_id: UUID, db: Session = Depends(get_db)) -> None:
    print(f"Received follow request for user_id: {user_id}")
    try:
        return follow_service.create_follow(db, user_id)
    except exc.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already following this user or the user does not exist.",
        )

@router.delete("/{user_id}/follow")
def delete_follow(user_id: UUID, db: Session = Depends(get_db)) -> None:
    if not follow_service.delete_follow(db, user_id):
        raise HTTPException(status_code=404, detail="User not found ")
    return {"message": "You are no longer following the user."}
