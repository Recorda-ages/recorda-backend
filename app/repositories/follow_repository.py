from uuid import UUID

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy import delete as delete_stmt
from sqlalchemy.orm import Session

from app.models.app_user import STATUS_ACTIVE, AppUser
from app.models.follow import STATUS_ACCEPTED, Follow

LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    for char in (LIKE_ESCAPE, "%", "_"):
        term = term.replace(char, LIKE_ESCAPE + char)
    return term


def _list_query(
    *,
    owner_side: ColumnElement,
    member_side: ColumnElement,
    owner_id: UUID,
    q: str | None,
) -> Select:

    stmt = (
        select(AppUser)
        .join(Follow, member_side == AppUser.user_id)
        .where(
            owner_side == owner_id,
            Follow.status == STATUS_ACCEPTED,
            AppUser.deleted_at.is_(None),
            AppUser.status == STATUS_ACTIVE,
        )
        # username é único, então ordenar por ele já é determinístico.
        .order_by(AppUser.username)
    )
    if q:
        stmt = stmt.where(
            AppUser.username.ilike(f"%{_escape_like(q)}%", escape=LIKE_ESCAPE)
        )
    return stmt


def _page(db: Session, stmt: Select, limit: int, offset: int) -> list[AppUser]:

    return list(db.scalars(stmt.limit(limit).offset(offset)))


def get_by_id(db: Session, follow_id: UUID) -> Follow | None:
    stmt = select(Follow).where(Follow.follow_id == follow_id)
    return db.scalars(stmt).first()


def get_by_users(db: Session, follower_id: UUID, following_id: UUID) -> Follow | None:
    stmt = select(Follow).where(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id,
    )
    return db.scalars(stmt).first()


def create(db: Session, follow: Follow) -> Follow:
    db.add(follow)
    db.flush()
    db.refresh(follow)
    return follow


def delete(db: Session, follow: Follow) -> None:
    db.delete(follow)
    db.commit()


def list_followers(
    db: Session, owner_id: UUID, *, q: str | None, limit: int, offset: int
) -> list[AppUser]:
    """Quem segue o dono da lista."""
    stmt = _list_query(
        owner_side=Follow.following_id,
        member_side=Follow.follower_id,
        owner_id=owner_id,
        q=q,
    )
    return _page(db, stmt, limit, offset)


def list_following(
    db: Session, owner_id: UUID, *, q: str | None, limit: int, offset: int
) -> list[AppUser]:
    """Quem o dono da lista segue."""
    stmt = _list_query(
        owner_side=Follow.follower_id,
        member_side=Follow.following_id,
        owner_id=owner_id,
        q=q,
    )
    return _page(db, stmt, limit, offset)


def is_accepted_follower(db: Session, follower_id: UUID, following_id: UUID) -> bool:
    stmt = select(Follow.follow_id).where(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id,
        Follow.status == STATUS_ACCEPTED,
    )
    return db.scalars(stmt).first() is not None


def remove_follower(db: Session, *, follower_id: UUID, following_id: UUID) -> bool:
    """Apaga o vínculo aceito. Retorna False se ele não existia."""
    stmt = delete_stmt(Follow).where(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id,
        Follow.status == STATUS_ACCEPTED,
    )
    removed = db.execute(stmt).rowcount
    db.commit()
    return removed > 0
