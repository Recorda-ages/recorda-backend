"""Pedidos para seguir contas privadas: aceitar, recusar e cancelar."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.time import now_utc
from app.models.app_user import AppUser
from app.models.follow import STATUS_ACCEPTED, STATUS_PENDING, Follow
from app.models.notification import TYPE_NEW_FOLLOWER
from app.repositories import follow_request_repository, notification_repository
from app.services import notification_service


class FollowRequestNotFoundError(Exception):
    """Pedido inexistente, já recusado ou já cancelado."""


class NotAllowedError(Exception):
    """O usuário não é a parte do pedido que pode fazer essa ação."""


class AlreadyResolvedError(Exception):
    """O pedido já foi aceito."""


def accept(db: Session, follow_id: UUID, current_user: AppUser) -> None:
    """Só quem recebeu o pedido aceita. Vira follow ativo e avisa quem pediu."""
    follow = _pending_for(db, follow_id, current_user, recipient=True)

    follow.status = STATUS_ACCEPTED
    follow.accepted_at = now_utc()
    notification_repository.convert_follow_request(
        db, follow.follow_id, TYPE_NEW_FOLLOWER
    )
    notification_service.notify_follow_accepted(db, follow)


def decline(db: Session, follow_id: UUID, current_user: AppUser) -> None:
    """Só quem recebeu o pedido recusa. Quem pediu não é avisado."""
    follow = _pending_for(db, follow_id, current_user, recipient=True)
    _discard(db, follow)


def cancel(db: Session, follow_id: UUID, current_user: AppUser) -> None:
    """Só quem fez o pedido cancela."""
    follow = _pending_for(db, follow_id, current_user, recipient=False)
    _discard(db, follow)


def _pending_for(
    db: Session, follow_id: UUID, current_user: AppUser, *, recipient: bool
) -> Follow:
    follow = follow_request_repository.get_for_update(db, follow_id)
    if follow is None:
        raise FollowRequestNotFoundError

    party_id = follow.following_id if recipient else follow.follower_id
    if current_user.user_id != party_id:
        db.rollback()
        raise NotAllowedError
    if follow.status != STATUS_PENDING:
        db.rollback()
        raise AlreadyResolvedError

    return follow


def _discard(db: Session, follow: Follow) -> None:
    notification_repository.delete_follow_request(db, follow.follow_id)
    follow_request_repository.delete(db, follow)
    db.commit()
