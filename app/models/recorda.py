from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Recorda(Base):
    __tablename__ = "recordas"

    id: Mapped[int] = mapped_column(primary_key=True)
    midia: Mapped[str] = mapped_column(String, nullable=True)
    music: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
    data: Mapped[str] = mapped_column(String, nullable=True)
