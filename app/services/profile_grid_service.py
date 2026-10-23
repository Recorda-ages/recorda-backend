"""Grade de Recordas de um perfil — paginada por cursor, respeitando privacidade."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.app_user import AppUser
from app.repositories import recorda_repository
from app.repositories.feed_repository import apply_cursor
from app.schemas.recorda import RecordaGridItem, RecordaGridPage
from app.services.feed_service import InvalidCursorError, _decode_cursor, _encode_cursor
from app.services.profile_service import (
    PrivateAccountError,
    UserNotFoundError,
    authorize_content_access,
    get_active_owner,
)


def get_profile_grid(
    db: Session,
    owner_id: UUID,
    viewer: AppUser,
    cursor: str | None,
    limit: int,
) -> RecordaGridPage:
    """Retorna a página da grade do perfil de owner_id para viewer.

    Levanta:
        UserNotFoundError  — dono inexistente, excluído ou suspenso.
        PrivateAccountError — conta privada e viewer sem acesso.
        InvalidCursorError  — cursor malformado.
    """
    owner = get_active_owner(db, owner_id)
    authorize_content_access(db, owner, viewer)

    cursor_created_at = cursor_recorda_id = None
    if cursor is not None:
        cursor_created_at, cursor_recorda_id = _decode_cursor(cursor)

    query = recorda_repository.get_profile_grid_query(owner_id)
    query = apply_cursor(query, cursor_created_at, cursor_recorda_id)
    query = query.limit(limit + 1)

    rows = db.scalars(query).all()

    has_next_page = len(rows) > limit
    page_rows = rows[:limit]

    items = [
        RecordaGridItem(
            recorda_id=r.recorda_id,
            media_url=r.media_url,
            media_type=r.media_type,
            song_title=r.song_title,
            song_artist_name=r.song_artist_name,
            song_cover_url=r.song_cover_url,
            created_at=r.created_at,
        )
        for r in page_rows
    ]

    next_cursor = None
    if has_next_page and items:
        last = page_rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.recorda_id)

    return RecordaGridPage(items=items, next_cursor=next_cursor)
