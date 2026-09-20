import base64
from datetime import datetime
from uuid import UUID

from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from app.repositories.feed_repository import apply_cursor, get_following_feed_query
from app.schemas.feed import FeedAuthor, FeedItem, FeedPage


class InvalidCursorError(Exception):
    """Cursor de paginação malformado ou corrompido."""


def _to_feed_item(row: Row) -> FeedItem:
    recorda = row.Recorda
    return FeedItem(
        recorda_id=recorda.recorda_id,
        author=FeedAuthor(
            user_id=recorda.user_id,
            username=row.username,
            profile_picture_url=row.profile_picture_url,
        ),
        media_url=recorda.media_url,
        media_type=recorda.media_type,
        description=recorda.description,
        song_title=recorda.song_title,
        song_artist_name=recorda.song_artist_name,
        song_cover_url=recorda.song_cover_url,
        song_preview_url=recorda.song_preview_url,
        likes_count=row.likes_count,
        is_liked=row.is_liked,
        created_at=recorda.created_at,
    )


def _encode_cursor(created_at: datetime, recorda_id: UUID) -> str:
    # "Opaco" pro cliente: ele só guarda essa string e devolve na
    # próxima chamada, sem precisar (nem poder) interpretar o conteúdo.
    raw = f"{created_at.isoformat()}|{recorda_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    # Caminho inverso: decodifica o base64 e separa os dois valores
    # de volta em (datetime, UUID) pra usar no apply_cursor().
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, recorda_id_str = raw.split("|", 1)
        return datetime.fromisoformat(created_at_str), UUID(recorda_id_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("Cursor inválido.") from exc


def get_following_feed(
    db: Session,
    current_user_id: UUID,
    cursor: str | None,
    limit: int,
) -> FeedPage:
    #Monta a página do feed 'seguindo' pro usuário autenticado.
    #Levanta InvalidCursorError se o cursor não puder ser decodificado.

    query = get_following_feed_query(current_user_id)

    cursor_created_at = cursor_recorda_id = None
    if cursor is not None:
        cursor_created_at, cursor_recorda_id = _decode_cursor(cursor)

    query = apply_cursor(query, cursor_created_at, cursor_recorda_id)

    # Peço um item a mais do que o limit pedido. Se vier essa linha extra,
    # sei que existe próxima página, sem precisar de um COUNT(*) separado.
    query = query.limit(limit + 1)

    rows = db.execute(query).all()

    has_next_page = len(rows) > limit
    page_rows = rows[:limit]

    items = [_to_feed_item(row) for row in page_rows]

    next_cursor = None
    if has_next_page and items:
        # O próximo cursor é baseado no ÚLTIMO item desta página (não no
        # item extra descartado) — é a partir dele que a próxima chamada
        # deve continuar.
        last_recorda = page_rows[-1].Recorda
        next_cursor = _encode_cursor(last_recorda.created_at, last_recorda.recorda_id)

    return FeedPage(items=items, next_cursor=next_cursor)