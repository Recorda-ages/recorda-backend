"""Aceitar, recusar e cancelar pedidos para seguir (T-E5.US21.BE.01)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AppUser
from app.schemas.follow_request import FollowRequestDecision
from app.services import follow_request_service as service

router = APIRouter(prefix="/follow-requests", tags=["follows"])

NOT_FOUND_MESSAGE = "Solicitação para seguir não encontrada."
ONLY_RECIPIENT_MESSAGE = "Apenas quem recebeu a solicitação pode respondê-la."
ONLY_SENDER_MESSAGE = "Apenas quem enviou a solicitação pode cancelá-la."
ALREADY_RESOLVED_MESSAGE = "Esta solicitação já foi aceita."


def _error(exc: Exception, forbidden_message: str) -> HTTPException:
    if isinstance(exc, service.NotAllowedError):
        return HTTPException(status.HTTP_403_FORBIDDEN, forbidden_message)
    if isinstance(exc, service.AlreadyResolvedError):
        return HTTPException(status.HTTP_409_CONFLICT, ALREADY_RESOLVED_MESSAGE)
    return HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_MESSAGE)


_ERRORS = (
    service.FollowRequestNotFoundError,
    service.NotAllowedError,
    service.AlreadyResolvedError,
)


@router.patch("/{follow_id}", status_code=status.HTTP_204_NO_CONTENT)
def respond_to_follow_request(
    follow_id: UUID,
    payload: FollowRequestDecision,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Aceita ou recusa um pedido recebido."""
    respond = service.accept if payload.action == "accept" else service.decline
    try:
        respond(db, follow_id, current_user)
    except _ERRORS as exc:
        raise _error(exc, ONLY_RECIPIENT_MESSAGE) from exc


@router.delete("/{follow_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_follow_request(
    follow_id: UUID,
    current_user: AppUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Cancela um pedido enviado que ainda não foi respondido."""
    try:
        service.cancel(db, follow_id, current_user)
    except _ERRORS as exc:
        raise _error(exc, ONLY_SENDER_MESSAGE) from exc
