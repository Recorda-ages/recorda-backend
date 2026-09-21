from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, tuple_

from app.models.app_user import STATUS_ACTIVE, AppUser
from app.models.follow import STATUS_ACCEPTED, Follow
from app.models.recorda import Recorda
from app.models.recorda_like import RecordaLike


def _likes_count_subquery():
    return (
        select(
            RecordaLike.recorda_id,
            func.count(RecordaLike.user_id).label("likes_count"),
        )
        .group_by(RecordaLike.recorda_id)
        .subquery()
    )


def _is_liked_subquery(current_user_id: UUID):
    return (
        select(RecordaLike.recorda_id)
        .where(
            RecordaLike.recorda_id == Recorda.recorda_id,
            RecordaLike.user_id == current_user_id,
        )
        .exists()
    )


def _visibility_condition(current_user_id: UUID | None = None):
    return Follow.status == STATUS_ACCEPTED


def get_following_feed_query(
    current_user_id: UUID,
):
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
        .join(Follow, Follow.following_id == AppUser.user_id)
        .outerjoin(
            likes_count_subq,
            likes_count_subq.c.recorda_id == Recorda.recorda_id,
        )
        .where(
            Follow.follower_id == current_user_id,
            _visibility_condition(current_user_id),
            Recorda.deleted_at.is_(None),
            AppUser.deleted_at.is_(None),
            AppUser.status == STATUS_ACTIVE,
        )
        # tie-breaker: garante ordem 100% determinística mesmo se duas
        # Recordas tiverem o created_at idêntico — sem isso, o cursor
        # poderia pular ou repetir uma delas entre páginas.
        .order_by(
            Recorda.created_at.desc(), Recorda.recorda_id.desc()
        )  # ordenado por data de criação, do mais recente para o mais antigo
    )


def apply_cursor(
    query: Select,
    cursor_created_at: datetime | None,
    cursor_recorda_id: UUID | None,
) -> Select:
    # Recebe a query já pronta e adiciona mais uma condição no WHERE,
    # só quando existe um cursor (ou seja, não é a primeira página).
    if cursor_created_at is None:
        return query

    return query.where(
        # Comparação de tupla: pega a PRÓXIMA linha depois da última que
        # o cliente já viu, respeitando a mesma ordem do order_by acima
        # (created_at DESC, recorda_id DESC como desempate).
        # SQL gerado: (created_at, recorda_id) < (cursor_created_at, cursor_recorda_id)
        tuple_(Recorda.created_at, Recorda.recorda_id)
        < tuple_(cursor_created_at, cursor_recorda_id)
    )
