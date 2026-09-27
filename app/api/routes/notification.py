"""Central de Notificações: listagem e leitura (T-E5.US26.BE.01)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.notification import NotificationPage
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage)
def list_notifications(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPage:
    """Notificações do usuário autenticado, da mais recente para a mais antiga."""
    return notification_service.list_notifications(
        db, current_user.user_id, limit=limit, offset=offset
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_as_read(
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Marca todas as notificações do usuário autenticado como lidas."""
    notification_service.mark_all_as_read(db, current_user.user_id)
