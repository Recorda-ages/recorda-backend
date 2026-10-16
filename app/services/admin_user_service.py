from app.models.app_user import AppUser
from app.schemas.admin_user import AdminUserPage, AdminUserRow


def search_users(db, q="", status=None, limit=20, offset=0):
    query = db.query(AppUser).filter(AppUser.deleted_at.is_(None))
    
    if q:
        query = query.filter(
            (
                AppUser.username.ilike(f"%{q}%"),
                AppUser.name.ilike(f"%{q}%"),
                AppUser.email.ilike(f"%{q}%"),
            )
        )

    if status:
        query = query.filter(AppUser.status == status)

    total = query.count()
    users, total = admin_user_repository.search_users(
    db, q=q, status=status, limit=limit, offset=offset
)
report_counts = admin_user_repository.count_reports_by_user(
    db, [user.user_id for user in users]
)
items = [
    _to_admin_user_row(user, report_counts.get(user.user_id, 0))
    for user in users
]
return AdminUserPage(items=items, total=total)