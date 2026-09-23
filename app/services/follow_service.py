"""Regras das listas de Seguidores/Seguindo: quem pode ver e quem sai."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.app_user import STATUS_ACTIVE, AppUser
from app.repositories import follow_repository, user_repository
from app.schemas.follow import FollowUser


class UserNotFoundError(Exception):
    """Dono da lista inexistente, removido ou suspenso."""


class PrivateAccountError(Exception):
    """Conta privada e o solicitante não é seguidor aceito dela."""


def _authorize(db: Session, owner_id: UUID, viewer: AppUser) -> None:
    """Deixa passar o dono, contas públicas e seguidores aceitos. Só isso."""
    owner = user_repository.get_by_id(db, owner_id)
    if owner is None or owner.status != STATUS_ACTIVE:
        raise UserNotFoundError
    if owner.user_id == viewer.user_id or not owner.is_private:
        return
    if not follow_repository.is_accepted_follower(db, viewer.user_id, owner.user_id):
        raise PrivateAccountError


def _normalize(q: str | None) -> str | None:
    q = q.strip() if q else ""
    return q or None


def list_followers(
    db: Session,
    owner_id: UUID,
    viewer: AppUser,
    *,
    q: str | None,
    limit: int,
    offset: int,
) -> list[FollowUser]:
    _authorize(db, owner_id, viewer)
    users = follow_repository.list_followers(
        db, owner_id, q=_normalize(q), limit=limit, offset=offset
    )
    return [FollowUser.model_validate(user) for user in users]


def list_following(
    db: Session,
    owner_id: UUID,
    viewer: AppUser,
    *,
    q: str | None,
    limit: int,
    offset: int,
) -> list[FollowUser]:
    _authorize(db, owner_id, viewer)
    users = follow_repository.list_following(
        db, owner_id, q=_normalize(q), limit=limit, offset=offset
    )
    return [FollowUser.model_validate(user) for user in users]


def remove_follower(db: Session, owner: AppUser, follower_id: UUID) -> bool:
    """Tira alguém dos seguidores do próprio usuário autenticado.

    Apagar a linha é o que faz o critério "em conta privada, o removido
    precisa solicitar novamente" valer: sem vínculo, um novo follow volta
    a nascer PENDING quando a BE#43 existir. Nenhuma notificação é
    publicada — nem há para onde publicar hoje (US26).
    """
    return follow_repository.remove_follower(
        db, follower_id=follower_id, following_id=owner.user_id
    )
