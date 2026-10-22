"""Persistence and query access for the Recorda entity."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models import AppUser, Recorda
from app.repositories._query import only_active_users, only_live
from app.repositories.general_feed_repository import _is_visible_to_user_condition


def get_all(db: Session) -> list[Recorda]:
    stmt = only_live(select(Recorda), Recorda).order_by(Recorda.created_at.desc())
    return list(db.scalars(stmt))


def list_visible_to_user(db: Session, viewer: AppUser) -> list[Recorda]:
    """Recordas não excluídas de autores ativos que `viewer` pode ver.

    Vale a mesma privacidade do detalhe: a própria conta, contas públicas e
    contas privadas com follow aceito.
    """
    stmt = (
        select(Recorda)
        .join(AppUser, Recorda.user_id == AppUser.user_id)
        .where(
            or_(
                AppUser.user_id == viewer.user_id,
                _is_visible_to_user_condition(viewer.user_id),
            )
        )
        .order_by(Recorda.created_at.desc())
    )
    return list(db.scalars(only_active_users(only_live(stmt, Recorda))))


def list_by_media_url(db: Session, media_url: str) -> list[Recorda]:
    """Inclui Recordas excluídas e de autores suspensos: decidem se a mídia foi publicada."""
    return list(db.scalars(select(Recorda).where(Recorda.media_url == media_url)))


def get_by_id(db: Session, recorda_id: UUID) -> Recorda | None:
    stmt = select(Recorda).where(Recorda.recorda_id == recorda_id)
    return db.scalars(only_live(stmt, Recorda)).first()


def get_by_id_including_deleted(db: Session, recorda_id: UUID) -> Recorda | None:
    """Administrative lookup, including removed content."""
    return db.scalar(select(Recorda).where(Recorda.recorda_id == recorda_id))


def list_by_user(db: Session, user_id: UUID) -> list[Recorda]:
    stmt = (
        select(Recorda)
        .where(Recorda.user_id == user_id)
        .order_by(Recorda.created_at.desc())
    )
    return list(db.scalars(only_live(stmt, Recorda)))


def count_by_user(db: Session, user_id: UUID) -> int:
    """Recordas vivas do usuário (contador do perfil).

    Não serve para o streak, que também considera Recordas excluídas.
    """
    stmt = select(func.count()).select_from(Recorda).where(Recorda.user_id == user_id)
    return db.scalar(only_live(stmt, Recorda)) or 0


def create(db: Session, recorda: Recorda) -> Recorda:
    db.add(recorda)
    db.commit()
    db.refresh(recorda)
    return recorda


def save(db: Session, recorda: Recorda) -> Recorda:
    db.commit()
    db.refresh(recorda)
    return recorda


def soft_delete(db: Session, recorda: Recorda) -> None:
    recorda.deleted_at = now_utc()
    db.commit()


def list_with_author_by_ids(db: Session, recorda_ids: Collection[UUID]) -> list[Row]:
    """Inclui Recordas excluídas: a moderação precisa ver o que foi denunciado."""
    stmt = (
        select(Recorda, AppUser.username)
        .join(AppUser, Recorda.user_id == AppUser.user_id)
        .where(Recorda.recorda_id.in_(recorda_ids))
    )
    return list(db.execute(stmt).all())
