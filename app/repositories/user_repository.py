"""Persistence and query access for the AppUser entity."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser, Follow
from app.repositories._query import only_live


def get_all(db: Session) -> list[AppUser]:
    return list(db.scalars(only_live(select(AppUser), AppUser)))


def get_by_id(db: Session, user_id: UUID) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.user_id == user_id)
    return db.scalars(only_live(stmt, AppUser)).first()


def get_by_username(
    db: Session, username: str, *, include_deleted: bool = False
) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.username == username)
    if not include_deleted:
        stmt = only_live(stmt, AppUser)
    return db.scalars(stmt).first()


def get_by_email(
    db: Session, email: str, *, include_deleted: bool = False
) -> AppUser | None:
    stmt = select(AppUser).where(AppUser.email == email)
    if not include_deleted:
        stmt = only_live(stmt, AppUser)
    return db.scalars(stmt).first()


def create(db: Session, user: AppUser) -> AppUser:
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save(db: Session, user: AppUser) -> AppUser:
    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, user: AppUser) -> None:
    user.deleted_at = now_utc()
    db.commit()


def search_by_username(
    db: Session, query: str, current_user_id: UUID, limit: int = 20
) -> list[tuple[AppUser, str | None]]:

    pattern = f"%{query}%"
    stmt = (
        select(AppUser, Follow.status)
        .outerjoin(
            Follow,
            (Follow.follower_id == current_user_id)
            & (Follow.following_id == AppUser.user_id),
        )
        .where(AppUser.username.ilike(pattern))
        .where(AppUser.user_id != current_user_id)
        .order_by(AppUser.username)
        .limit(limit)
    )
    stmt = only_live(stmt, AppUser)
    return list(db.execute(stmt).all())


def list_suggestion_candidates(db: Session, current_user_id: UUID) -> list[AppUser]:
    """Usuários elegíveis a virar sugestão para `current_user_id`.

    Aplica os três critérios de exclusão da US27 de uma vez: fora o próprio
    usuário e fora quem já tem qualquer vínculo de follow partindo dele —
    uma linha ACCEPTED cobre "já seguido" e uma PENDING cobre "solicitação
    pendente". Apagados também ficam de fora, como manda o D34 do modelo de
    dados, que cita sugestões explicitamente.

    Não aplica limite: o corte acontece depois do ranqueamento por afinidade,
    que é feito em memória.
    """
    already_linked = select(Follow.following_id).where(
        Follow.follower_id == current_user_id
    )
    stmt = (
        select(AppUser)
        .where(AppUser.user_id != current_user_id)
        .where(AppUser.user_id.not_in(already_linked))
    )
    return list(db.scalars(only_live(stmt, AppUser)))
