"""Regras das listas de Seguidores/Seguindo: quem pode ver e quem sai."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models.app_user import STATUS_ACTIVE, AppUser
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING, Follow
from app.repositories import follow_repository, user_repository
from app.schemas.follow import FollowUser
from app.services import notification_service


class FollowTargetNotFoundError(Exception):
    """O perfil não existe, foi removido ou está suspenso."""


class SelfFollowError(Exception):
    """A pessoa tentou seguir o próprio perfil."""


class DuplicateFollowError(Exception):
    """Já existe um follow ou solicitação entre as duas contas."""


def create_follow(db: Session, user_id: UUID, current_user: AppUser) -> str:
    if current_user.user_id == user_id:
        raise SelfFollowError

    target_user = user_repository.get_by_id(db, user_id)
    if target_user is None or target_user.status != STATUS_ACTIVE:
        raise FollowTargetNotFoundError
    if follow_repository.get_by_users(db, current_user.user_id, user_id) is not None:
        raise DuplicateFollowError

    requested_at = now_utc()
    is_private = target_user.is_private
    follow = Follow(
        follower_id=current_user.user_id,
        following_id=user_id,
        status=STATUS_PENDING if is_private else STATUS_ACCEPTED,
        requested_at=requested_at,
        accepted_at=None if is_private else requested_at,
    )
    try:
        follow_repository.create(db, follow)
    except IntegrityError as exc:
        db.rollback()
        if (
            follow_repository.get_by_users(db, current_user.user_id, user_id)
            is not None
        ):
            raise DuplicateFollowError from exc
        raise
    if is_private:
        notification_service.notify_follow_request(db, follow)
        return "solicitado"

    notification_service.notify_new_follower(db, follow)
    return "seguindo"


def delete_follow(db: Session, user_id: UUID, current_user: AppUser) -> bool:
    follow = follow_repository.get_by_users(db, current_user.user_id, user_id)
    if follow is None:
        return False
    follow_repository.delete(db, follow)
    return True


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
