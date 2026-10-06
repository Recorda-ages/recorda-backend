"""Router administrativo /admin com a guarda de admin aplicada no router (T-E10.BE.01)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin_user)],
)
