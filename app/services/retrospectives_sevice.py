from datetime import datetime

from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser

def get_available_periods(db: Session, viewer: AppUser) -> None:
