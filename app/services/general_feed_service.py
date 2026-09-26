"""Orquestração do feed da aba Geral (GET /feed/general).

Junta duas regras: acesso (quem o usuário pode ver, resolvido no repository)
e Afinidade Musical > 0 (affinity_service.calculate_affinity, issue #38).
"""

from uuid import UUID

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.repositories import general_feed_repository
from app.repositories.feed_repository import apply_cursor
from app.schemas.feed import FeedPage
from app.services.affinity_service import calculate_affinity
from app.services.feed_service import (
    InvalidCursorError,
    _decode_cursor,
    _encode_cursor,
    _to_feed_item,
)

# InvalidCursorError é reexportado para a rota tratar o erro a partir deste módulo.
__all__ = ["InvalidCursorError", "get_general_feed"]


def _get_eligible_author_ids(db: Session, current_user_id: UUID) -> list[UUID]:
    candidate_ids = general_feed_repository.get_candidate_author_ids(
        db, current_user_id
    )
    return [
        candidate_id
        for candidate_id in candidate_ids
        if calculate_affinity(db, current_user_id, candidate_id) > 0
    ]


def _build_page(rows: list[Row], limit: int) -> FeedPage:
    # rows vem com até limit + 1 linhas: a extra só indica que existe próxima página.
    page_rows = rows[:limit]
    items = [_to_feed_item(row) for row in page_rows]

    next_cursor = None
    if len(rows) > limit and page_rows:
        last_recorda = page_rows[-1].Recorda
        next_cursor = _encode_cursor(last_recorda.created_at, last_recorda.recorda_id)

    return FeedPage(items=items, next_cursor=next_cursor)


def get_general_feed(
    db: Session,
    current_user_id: UUID,
    cursor: str | None,
    limit: int,
) -> FeedPage:
    """Monta a página do feed Geral. Levanta InvalidCursorError se o cursor for inválido."""
    cursor_created_at = cursor_recorda_id = None
    if cursor is not None:
        # Decodifica antes de tocar no banco: um cursor inválido não deve
        # disparar as queries de afinidade.
        cursor_created_at, cursor_recorda_id = _decode_cursor(cursor)

    author_ids = _get_eligible_author_ids(db, current_user_id)
    if not author_ids:
        return FeedPage(items=[], next_cursor=None)

    query = general_feed_repository.get_general_feed_query(current_user_id, author_ids)
    query = apply_cursor(query, cursor_created_at, cursor_recorda_id).limit(limit + 1)
    rows = db.execute(query).all()

    return _build_page(rows, limit)
