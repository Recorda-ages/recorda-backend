# Criei esse model, que estava faltando para representar a tabela follow do banco de dados 4.2 na wiki.
# Ainda falta o alembic, então por favor não rodar o migrate ainda, senão vai dar erro.
# O model é só pra poder escrever a query do feed (que precisa filtrar por Follow.status = "ACEPTED" para contas privadas) e escrever os testes unitários da query.
# Depois que o alembic estiver pronto, aí sim podemos rodar o migrate e criar a tabela no banco.
# Como isso foge do meu conhecimento de validação de dados, por favor me avisem se tiver algum detalhe que eu tenha esquecido de colocar no model.
# Assim como o alembic e criação do banco é responsabilidade do time de infra, a validação de dados é responsabilidade do time de backend.
# Eu só fiz o model pra poder escrever a query do feed e os testes unitários da query, mas não posso validar se o model está correto ou não.
# Ultima obs: segui o padrao dos demais models e as regras de negócio da wiki, mas não sei se está correto.

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import now_utc
from app.db.session import Base

STATUS_PENDING = "PENDING"
STATUS_ACCEPTED = "ACCEPTED"


class Follow(Base):
    __tablename__ = "follow"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED')", name="ck_follow_status"
        ),
        CheckConstraint(
            "follower_id <> following_id", name="ck_follow_no_self_follow"
        ),
        UniqueConstraint(
            "follower_id", "following_id", name="uq_follow_follower_id_following_id"
        ),
        Index("ix_follow_follower_id", "follower_id"),
    )

    follow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    follower_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    following_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
        server_default=func.now(),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
