"""Regra de privacidade unificada para acesso ao conteúdo de um perfil."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.app_user import STATUS_ACTIVE, AppUser
from app.repositories import follow_repository, user_repository


class UserNotFoundError(Exception):
    """Dono do perfil inexistente, excluído ou suspenso."""


class PrivateAccountError(Exception):
    """Conta privada e o visitante não é seguidor aceito."""


def get_active_owner(db: Session, owner_id: UUID) -> AppUser:
    """Retorna o dono se existir e estiver ativo; levanta UserNotFoundError caso contrário."""
    owner = user_repository.get_by_id(db, owner_id)
    if owner is None or owner.status != STATUS_ACTIVE:
        raise UserNotFoundError
    return owner


def can_view_content(db: Session, owner: AppUser, viewer: AppUser) -> bool:
    """Dono, conta pública ou seguidor ACCEPTED podem ver o conteúdo. Retorna True ou False."""
    if owner.user_id == viewer.user_id or not owner.is_private:
        return True
    return follow_repository.is_accepted_follower(db, viewer.user_id, owner.user_id)


def authorize_content_access(db: Session, owner: AppUser, viewer: AppUser) -> None:
    """Levanta PrivateAccountError se viewer não tiver acesso ao perfil de owner."""
    if not can_view_content(db, owner, viewer):
        raise PrivateAccountError
