from sqlalchemy import Select


def only_live(stmt: Select, model) -> Select:
    return stmt.where(model.deleted_at.is_(None))
