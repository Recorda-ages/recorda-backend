from sqlalchemy.orm import Session

from app.models.app_user import STATUS_ACTIVE
from app.services import admin_user_moderation_service
from tests.factories import add_report, add_user


def test_search_users_returns_report_counts(db: Session):
    target = add_user(db, "search_target")
    add_report(db, add_user(db, "search_reporter"), reported_user=target)

    result = admin_user_moderation_service.search_users(
        db, q="target", status=None, limit=10, offset=0
    )

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].user_id == target.user_id
    assert result.items[0].status == STATUS_ACTIVE
    assert result.items[0].reports_count == 1
