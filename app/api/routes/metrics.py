from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.metrics import MetricsPeriod, ProfileMetricsResponse
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
