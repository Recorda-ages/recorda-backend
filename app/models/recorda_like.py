# Criei esse model, que estava faltando para representar a tabela RecordaLike do banco de dados 4.8 na wiki.
# Ainda falta o alembic, então por favor não rodar o migrate ainda, senão vai dar erro.
# O model é só pra poder escrever a query do feed e escrever os testes unitários da query.
# Depois que o alembic estiver pronto, aí sim podemos rodar o migrate e criar a tabela no banco.
# Como isso foge do meu conhecimento de validação de dados, por favor me avisem se tiver algum detalhe que eu tenha esquecido de colocar no model.
# Assim como o alembic e criação do banco é responsabilidade do time de infra, a validação de dados é responsabilidade do time de backend.
# Eu só fiz o model pra poder escrever a query do feed e os testes unitários da query, mas não posso validar se o model está correto ou não.
# Ultima obs: segui o padrao dos demais models e as regras de negócio da wiki, mas não sei se está correto.

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base


class RecordaLike(Base):
    __tablename__ = "recorda_like"
    __table_args__ = (Index("ix_recorda_like_recorda_id", "recorda_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), primary_key=True
    )
    recorda_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recorda.recorda_id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
