
from http.client import HTTPException
from uuid import UUID

from app.models.app_user import AppUser
import app.repositories.admin_user_status_repository as set_status, get_for_update



def suspend_user(db: Session, user_id: UUID, current_admin, *, resolve_reports: bool, record_action: str) -> None:
    user = get_for_update(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")
    if user.status == "suspended":
        raise HTTPException(status_code=409, detail=f"User with ID {user_id} is already suspended.")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot suspend yourself.")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="You cannot suspend another admin user.")
    try:
        set_status(db, user, "suspended")
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise e

def reactivate_user(db: Session, admin_user: AppUser, * , target_user_id: UUID, record_action: str) -> None:
    user = get_for_update(db, target_user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {target_user_id} not found.")
    if user.status != "suspended":
        raise HTTPException(status_code=409, detail=f"User with ID {target_user_id} is not suspended.")
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="You cannot reactivate yourself.")
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="You cannot reactivate another admin user.")
    try:
        set_status(db, user, "active")
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise e