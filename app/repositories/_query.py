from sqlalchemy import Select, and_

from app.models.app_user import STATUS_ACTIVE, AppUser


def only_live(stmt: Select, model) -> Select:
    return stmt.where(model.deleted_at.is_(None))


def active_user_condition(user_model=AppUser):
    """Conta não excluída e ACTIVE. Aceita aliases de AppUser.

    Existe separada de `only_active_users` para caber dentro de um OR,
    como nas notificações de sistema, que não têm remetente.
    """
    return and_(user_model.deleted_at.is_(None), user_model.status == STATUS_ACTIVE)


def only_active_users(stmt: Select, user_model=AppUser) -> Select:
    """Filtra contas suspensas e excluídas. Não cria o JOIN com `user_model`."""
    return stmt.where(active_user_condition(user_model))
