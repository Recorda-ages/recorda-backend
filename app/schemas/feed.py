#schemas Pydantic de request/response (ex: FeedItemResponse com avatar, username, mídia, música, descrição, curtidas, etc.

# app/schemas/feed.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FeedAuthor(BaseModel):
    # Dados do autor da Recorda que aparecem no card do feed.
    # Não é o AppUser inteiro — só o que a tela precisa mostrar.
    user_id: UUID
    username: str
    avatar_url: str | None = None


class FeedItem(BaseModel):
    # Um item do feed = uma Recorda + dados agregados (curtidas) +
    # dados do autor "achatados" junto (evita o client ter que
    # fazer outra chamada pra saber quem publicou).
    model_config = ConfigDict(from_attributes=True)
    # from_attributes=True permite montar esse schema direto a partir
    # do objeto ORM Recorda (Recorda.recorda_id vira recorda_id, etc.),
    # em vez de precisar passar um dict manualmente.

    recorda_id: UUID
    author: FeedAuthor

    media_url: str
    media_type: str  # 'PHOTO' | 'VIDEO'
    description: str | None = None

    song_title: str
    song_artist_name: str
    song_cover_url: str
    song_preview_url: str | None = None

    likes_count: int
    is_liked: bool

    created_at: datetime


class FeedPage(BaseModel):
    # Envelope de paginação: os itens da página atual + o cursor pra
    # pedir a próxima. next_cursor=None sinaliza "acabou o feed".
    items: list[FeedItem]
    next_cursor: str | None = None