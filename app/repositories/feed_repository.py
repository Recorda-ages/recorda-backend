##a query que busca Recordas de autores seguidos, respeitando aprovação de contas privadas, ordenação e paginação por cursor

from uuid import UUID

from sqlalchemy import select, or_, func, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.follow import Follow
from app.models.user import AppUser
from app.models.recorda import Recorda
from app.models.recorda_like import RecordaLike

#OBS: resolvi isolar as queries para poder testar individualmente, bem como deixar mais limpo o código, e permitir reaproveitamento em outros lugares (ex: página de perfil de um usuário seguido, busca, etc).

def _likes_count_subquery():
    # Isolei essa subquery numa função própria porque ela representa uma ideia fechada: "quantas curtidas cada recorda_id tem".
    # Fica reaproveitável se algum dia precisar de likes_count em outro lugar, e também deixa a query principal mais limpa.
    return (
        select(
            RecordaLike.recorda_id,
            func.count(RecordaLike.user_id).label("likes_count"), 
        )
        .group_by(RecordaLike.recorda_id)
        .subquery() #transforma em subquery para poder ser usada depois.
    )

def _is_liked_subquery(current_user_id: UUID):
    # Mesma ideia: "o usuário logado curtiu essa recorda?" isolado numa função própria, para deixar a query principal mais limpa.
    return (
        select(RecordaLike.recorda_id)
        .where(
            RecordaLike.recorda_id == Recorda.recorda_id,
            RecordaLike.user_id == current_user_id, #o usuário logado é quem está pedindo o feed, então a query vai verificar se ele curtiu cada recorda_id do feed.
        )
        .exists()
    )

def _visibility_condition(current_user_id: UUID):
    # Botei num nome próprio porque essa condição pode a ser reaproveitada em outros lugares (ex: página de perfil de um
    # usuário seguido, busca, etc), não só no feed.
    return or_(
        AppUser.is_private.is_(False),  #contas públicas: is_private = False
        Follow.status == "ACEPTED", #contas privadas: só traz se o status do follow for "ACEPTED"
    )

#função que monta, mas não executa a query:
def get_following_feed_query(current_user_id: UUID): # Recebe o id do usuário logado, que é quem está pedindo o feed "Seguindo"
   
    likes_count_subq = _likes_count_subquery()

    return (
        select(
            Recorda, #ponto de partida é o objetivo final - os recordas
            AppUser.username, #username e avatar_url do autor da Recorda, que estão na tabela AppUser
            AppUser.profile_picture_url,
            func.coalesce(likes_count_subq.c.likes_count, 0).label("likes_count"),
            _is_liked_subquery(current_user_id).label("is_liked"),
        )
        .join(AppUser, Recorda.user_id == AppUser.user_id) #Junta Recorda com AppUser usando a FK recorda.user_id
        .join(Follow, Follow.following_id == AppUser.user_id) #Junta com Follow: following_id (quem é seguido) tem que bater com o user_id do autor da Recorda que acabamos de trazer no join anterior.
        .outerjoin( # opto pelo LEFT JOIN porque eu usasse INNER JOIN com a subquery de contagem, os Recordas com zero curtidas (que não têm linha na subquery) desapareceriam do resultado, e elas precisam aparecer, com likes_count = 0.
            likes_count_subq,
            likes_count_subq.c.recorda_id == Recorda.recorda_id,
        )
        .where(
            Follow.follower_id == current_user_id,#só as linhas em que quem está seguindo é o usuário logado.
            _visibility_condition(current_user_id), #chamo as condições de aceite de viasualização.
            Recorda.deleted_at.is_(None), #não aparece recordas deletados no feed
        ) 
        # tie-breaker: garante ordem 100% determinística mesmo se duas
        # Recordas tiverem o created_at idêntico — sem isso, o cursor
        # poderia pular ou repetir uma delas entre páginas.
        .order_by(Recorda.created_at.desc(), Recorda.recorda_id.desc()) #ordenado por data de criação, do mais recente para o mais antigo
    ) 

def apply_cursor(query, cursor_created_at, cursor_recorda_id):
    # Recebe a query já pronta e adiciona mais uma condição no WHERE,
    # só quando existe um cursor (ou seja, não é a primeira página).
    if cursor_created_at is None:
        return query

    return query.where(
        # Comparação de tupla: pega a PRÓXIMA linha depois da última que
        # o cliente já viu, respeitando a mesma ordem do order_by acima
        # (created_at DESC, recorda_id DESC como desempate).
        # SQL gerado: (created_at, recorda_id) < (cursor_created_at, cursor_recorda_id)
        tuple_(Recorda.created_at, Recorda.recorda_id)
        < tuple_(cursor_created_at, cursor_recorda_id)
    )


