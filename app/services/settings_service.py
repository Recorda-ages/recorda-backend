from sqlalchemy.orm import Session

from app.models import AppUser
from app.repositories import follow_request_repository, user_repository
from app.schemas.settings import UserSettingsResult, UserSettingsUpdate
from app.services import follow_request_service


def update(
    db: Session, user: AppUser, payload: UserSettingsUpdate
) -> UserSettingsResult:
    accepted_requests = 0
    try:
        user = user_repository.get_for_update(db, user.user_id)
        if payload.language is not None:
            user.language = payload.language
        if payload.is_private is not None and payload.is_private != user.is_private:
            user.is_private = payload.is_private
            if not user.is_private:
                pending = follow_request_repository.list_pending_for_update(
                    db, user.user_id
                )
                for follow in pending:
                    follow_request_service._accept(db, follow)
                accepted_requests = len(pending)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return UserSettingsResult(
        is_private=user.is_private,
        language=user.language,
        accepted_requests=accepted_requests,
    )
