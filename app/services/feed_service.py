#a lógica de orquestração: chama o repository, aplica as regras de negócio (quem é seguido, contas privadas aprovadas, etc.) e monta a resposta

#Importo a função que monta a query (não executa nada sozinha) e os schemas Pydantic que definem o formato da resposta.
import base64
from datetime import datetime
from uuid import UUID

from app.repositories.feed_repository import apply_cursor, get_following_feed_query
from app.schemas.feed import FeedItem, FeedAuthor, FeedPage

def _to_feed_item(row) -> FeedItem: #Recebe uma linha do resultado da query e devolve um FeedItem já validado pelo Pydantic.
    recorda, username, profile_picture_url, likes_count, is_liked = row #IMPORTANTE: A ordem aqui precisa bater exatamente com a ordem das colunas no select() do feed_repository.py

    return FeedItem( #então acesso os campos dele por atributo, não por dict.
        recorda_id=recorda.recorda_id, #é o mesmo valor que o AppUser.user_id do join, só que já está disponível direto na Recorda.
        author=FeedAuthor(
            user_id=recorda.user_id, #Esses dois vieram como colunas soltas da query (não fazem parte do objeto Recorda), por isso uso as variáveis desempacotadas direto, e renomeio profile_picture_url -> avatar_url pra bater com o nome do campo no schema FeedAuthor.
            username=username,
            avatar_url=profile_picture_url,
        ),#Campos que vêm direto da tabela recorda, sem transformação:
        media_url=recorda.media_url,
        media_type=recorda.media_type,
        description=recorda.description,
        song_title=recorda.song_title,
        song_artist_name=recorda.song_artist_name,
        song_cover_url=recorda.song_cover_url,
        song_preview_url=recorda.song_preview_url,
        likes_count=likes_count, #Esses dois vêm das subqueries (_likes_count_subquery e _is_liked_subquery) já calculados no banco, o service só repassa, não recalcula nada.
        is_liked=is_liked,
        created_at=recorda.created_at,
    )

def _encode_cursor(created_at: datetime, recorda_id: UUID) -> str:
    # Junto os dois valores num texto simples e codifico em base64.
    # "Opaco" pro cliente: ele só guarda essa string e devolve na
    # próxima chamada, sem precisar (nem poder) interpretar o conteúdo.
    raw = f"{created_at.isoformat()}|{recorda_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    # Caminho inverso: decodifica o base64 e separa os dois valores
    # de volta em (datetime, UUID) pra usar no apply_cursor().
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    created_at_str, recorda_id_str = raw.split("|")
    return datetime.fromisoformat(created_at_str), UUID(recorda_id_str)



async def get_following_feed( #função pública do service, é o que o api/routes/feed.py vai chamar. Ela orquestra tudo: pega a query do repository, aplica a paginação, executa no banco, transforma cada linha em FeedItem (usando a função de cima) e devolve um FeedPage pronto pra virar a resposta HTTP.
    db: AsyncSession,
    current_user_id: UUID,
    cursor: str | None,
    limit: int,
) -> FeedPage:
    query = get_following_feed_query(current_user_id)

 
    cursor_created_at = cursor_recorda_id = None
    if cursor is not None:
        # Só decodifica se o cliente mandou um cursor (páginas depois
        # da primeira). Se vier um cursor corrompido/inválido, o ValueError
        # do fromisoformat/UUID sobe naturalmente — vale a camada de rota
        # tratar isso como 400 Bad Request.
        cursor_created_at, cursor_recorda_id = _decode_cursor(cursor)

    query = apply_cursor(query, cursor_created_at, cursor_recorda_id)

    # Peço um item a mais do que o limit pedido. Se vier essa linha extra,
    # sei que existe próxima página, sem precisar de um COUNT(*) separado.
    query = query.limit(limit + 1)

    result = await db.execute(query)
    rows = result.all()

    has_next_page = len(rows) > limit
    # Descarto a linha extra antes de montar a resposta, ela só serve
    # como "sinalizador", não deve aparecer pro cliente.
    page_rows = rows[:limit]

    items = [_to_feed_item(row) for row in page_rows]

    next_cursor = None
    if has_next_page and items:
        # O próximo cursor é baseado no ÚLTIMO item desta página (não no
        # item extra descartado) — é a partir dele que a próxima chamada
        # deve continuar.
        last_recorda = page_rows[-1][0]  # [0] = objeto Recorda na tupla
        next_cursor = _encode_cursor(last_recorda.created_at, last_recorda.recorda_id)

    return FeedPage(items=items, next_cursor=next_cursor)