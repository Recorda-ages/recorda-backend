from uuid import UUID
from app.api.deps import get_current_user
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import AppUser, Follow
from app.repositories import user_repository


def create_follow(db: Session, user_id: UUID, current_user: AppUser) -> None:
    print(f"Creating follow relationship: user_id={user_id}")
    print(f"Current user: {current_user.user_id}")
    # Obtém o usuário autenticado (sessão) usando a dependência get_current_user
    if current_user.user_id == user_id:
        raise ValueError("Você não pode seguir a si mesmo.")

    # Verifica se conta do user_id é privada
    #is_private = user_repository.is_user_private(db, user_id)
    
    #if is_private:
       # return "Requisição de follow enviada para o usuário privado."  # Retorna uma mensagem de sucesso
        # Se o usuário for privado, cria uma solicitação de follow
        # solicitation = user_repository.create_follow_request(db, payload)
        # Aqui você pode adicionar lógica para enviar notificação ao usuário privado sobre a solicitação de follow
        # Se o usuário for público, cria o follow direto
        # solicitation = user_repository.create_follow(db, payload)
        #pass
    return "Você está seguindo o usuário público."  # Retorna uma mensagem de sucesso


def delete_follow(db: Session, user_id: UUID) -> None:
    return ""  # Retorna uma mensagem de sucesso 