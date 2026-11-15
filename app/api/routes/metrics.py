from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.metrics import MetricsPeriod, ProfileMetricsResponse
from app.services import profile_service
from app.services.metrics.engine import MetricsEngine

router = APIRouter(prefix="/users/me/metrics", tags=["metrics"])


@router.get("", response_model=ProfileMetricsResponse)
def get_profile_metrics(
    period: MetricsPeriod = MetricsPeriod.ALL_TIME,
    bundle: Literal["profile"] = "profile",
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileMetricsResponse:
    return MetricsEngine().profile(db, current_user.user_id, period)


user_metrics_router = APIRouter(prefix="/users/{user_id}/metrics", tags=["metrics"])


@user_metrics_router.get("", response_model=ProfileMetricsResponse)
def get_user_profile_metrics(
    user_id: UUID,
    period: MetricsPeriod = MetricsPeriod.ALL_TIME,
    bundle: Literal["profile"] = "profile",
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileMetricsResponse:
    """Métricas do perfil de outro usuário, respeitando a privacidade (D-06)."""
    try:
        owner = profile_service.get_viewable_owner(db, user_id, current_user)
    except profile_service.UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        ) from exc
    except profile_service.PrivateAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta conta é privada.",
        ) from exc
    return MetricsEngine().profile(db, owner.user_id, period)
