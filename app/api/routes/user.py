from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_current_user
from app.api.routes.auth import user_already_exists_error
from app.db.session import get_db
from app.models import AppUser
from app.schemas.follow_mutation import FollowMutationResult
from app.schemas.music_preference import (
    MusicPreferencesCreate,
    MusicPreferencesRead,
)
from app.schemas.user import (
    SuggestedUser,
    UserChangeRole,
    UserCreate,
    UserProfileRead,
    UserRead,
    UserSearchResult,
    UserUpdate,
)
from app.services import (
    admin_user_moderation_service,
    follow_service,
    music_preference_service,
    user_service,
)

router = APIRouter(prefix="/users", tags=["users"])

_current_admin = Depends(get_current_admin_user)


@router.get("/search", response_model=list[UserSearchResult])
def search_users(
    q: str = Query(default=""),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSearchResult]:
    return user_service.search_by_username(db, q, current_user.user_id)


@router.get("/suggestions", response_model=list[SuggestedUser])
def suggest_users(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestedUser]:
    return user_service.suggest_by_affinity(db, current_user.user_id)


@router.get("/me/profile", response_model=UserProfileRead)
def get_own_profile(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    try:
        return user_service.get_own_profile(db, current_user)
    except user_service.IncompleteProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complete o onboarding musical para acessar o perfil.",
        ) from exc


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


@router.post("/{user_id}/follow", response_model=FollowMutationResult)
def create_follow(
    user_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowMutationResult:
    try:
        follow_status = follow_service.create_follow(db, user_id, current_user)
    except follow_service.SelfFollowError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode seguir a si mesmo.",
        ) from exc
    except follow_service.DuplicateFollowError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já segue ou solicitou seguir este usuário.",
        ) from exc
    except follow_service.FollowTargetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        ) from exc
    return FollowMutationResult(follow_status=follow_status)


@router.delete("/{user_id}/follow", response_model=FollowMutationResult)
def delete_follow(
    user_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowMutationResult:
    if not follow_service.delete_follow(db, user_id, current_user):
        raise HTTPException(status_code=404, detail="Você não segue este usuário.")
    return FollowMutationResult(follow_status="nenhuma")


@router.post("/users/{user_id}/suspend", status_code=status.HTTP_200_OK)
def suspend_user(
    user_id: UUID,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        admin_user_moderation_service.suspend_user(db, user_id, current_admin)
    except user_service.UserNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found."
        ) from exc
    except user_service.SelfActionError as exc:
        raise HTTPException(
            status_code=400, detail="You cannot suspend yourself."
        ) from exc
    except user_service.AdminActionError as exc:
        raise HTTPException(
            status_code=403, detail="You cannot suspend another admin user."
        ) from exc
    except user_service.UserAlreadySuspendedError as exc:
        raise HTTPException(
            status_code=409, detail=f"User with ID {user_id} is already suspended."
        ) from exc


@router.post("/users/{user_id}/reactivate", status_code=status.HTTP_200_OK)
def reactive_user(
    user_id: UUID,
    current_admin: AppUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        admin_user_moderation_service.reactivate_user(db, user_id, current_admin)
    except user_service.UserNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"User with ID {user_id} not found."
        ) from exc
    except user_service.UserNotSuspendedError as exc:
        raise HTTPException(
            status_code=409, detail=f"User with ID {user_id} is not suspended."
        ) from exc
