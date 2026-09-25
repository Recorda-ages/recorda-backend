"""Queries do feed da aba Geral (GET /feed/general).

A regra de Afinidade Musical não fica aqui: ela é aplicada no service via
affinity_service.calculate_affinity (fonte única da regra, issue #38).
Este módulo só resolve quem o usuário pode ver e busca as Recordas desses autores.
"""

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.app_user import STATUS_ACTIVE, AppUser
from app.models.follow import STATUS_ACCEPTED, Follow
from app.models.recorda import Recorda
from app.repositories.feed_repository import _is_liked_subquery, _likes_count_subquery


def _is_accepted_follower_condition(current_user_id: UUID):
    # EXISTS em vez de JOIN: aqui o follow é opcional (fica dentro de um OR
    # com "perfil público"). Um JOIN excluiria as contas públicas não seguidas.
    return (
        select(Follow.follow_id)
        .where(
            Follow.follower_id == current_user_id,
            Follow.following_id == AppUser.user_id,
            Follow.status == STATUS_ACCEPTED,
        )
        .exists()
    )


def _is_visible_to_user_condition(current_user_id: UUID):
    # Privacidade vive no perfil: conta pública é visível para todos;
    # conta privada só para quem a segue com o pedido aceito.
    return or_(
        AppUser.is_private.is_(False),
        _is_accepted_follower_condition(current_user_id),
    )


def get_candidate_author_ids(db: Session, current_user_id: UUID) -> list[UUID]:
    """Autores que o usuário pode ver, antes do filtro de afinidade."""
    stmt = select(AppUser.user_id).where(
        AppUser.deleted_at.is_(None),
        AppUser.status == STATUS_ACTIVE,
        # O próprio post não entra: o app o exibe localmente logo após a publicação.
        AppUser.user_id != current_user_id,
        _is_visible_to_user_condition(current_user_id),
    )
    return list(db.scalars(stmt))


def get_general_feed_query(current_user_id: UUID, author_ids: list[UUID]) -> Select:
    """Recordas dos autores informados, da mais recente para a mais antiga.

    Espera author_ids já filtrados por acesso e afinidade (ver
    get_candidate_author_ids e general_feed_service).
    """
    likes_count_subq = _likes_count_subquery()

    return (
        select(
            Recorda,
            AppUser.username,
            AppUser.profile_picture_url,
            func.coalesce(likes_count_subq.c.likes_count, 0).label("likes_count"),
            _is_liked_subquery(current_user_id).label("is_liked"),
        )
        .join(AppUser, Recorda.user_id == AppUser.user_id)
        .outerjoin(
            likes_count_subq,
            likes_count_subq.c.recorda_id == Recorda.recorda_id,
        )
        .where(
            Recorda.user_id.in_(author_ids),
            Recorda.deleted_at.is_(None),
        )
        # Mesmo desempate do feed Seguindo, para o apply_cursor funcionar igual.
        .order_by(Recorda.created_at.desc(), Recorda.recorda_id.desc())
    )
