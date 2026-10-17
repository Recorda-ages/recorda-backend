from sqlalchemy.orm import Session

from app.repositories import admin_user_repository
from app.schemas.admin_user import AdminUserPage


def search_users(
    db: Session, *, q: str, status: str | None, limit: int, offset: int
) -> AdminUserPage:
    users, total = admin_user_repository.search_users(
        db, q=q, status=status, limit=limit, offset=offset
    )
    report_counts = admin_user_repository.count_reports_by_user(
        db, [user.user_id for user in users]
    )
    items = [
        admin_user_repository.to_admin_user_row(
            user, report_counts.get(user.user_id, 0)
        )
        for user in users
    ]
    return AdminUserPage(items=items, total=total)
