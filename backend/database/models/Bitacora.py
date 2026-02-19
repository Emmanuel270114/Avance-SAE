from ..db_base import Base

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class Bitacora(Base):
    __tablename__ = "Bitacora"

    Id_Bitacora: Mapped[int] = mapped_column(primary_key=True, index=True)
    Id_Usuario: Mapped[int] = mapped_column(nullable=False)
    Id_Modulo: Mapped[int] = mapped_column(nullable=False)
    Id_Periodo: Mapped[int] = mapped_column(nullable=True)
    Acciones: Mapped[str] = mapped_column(String(256), nullable=False)
    Host: Mapped[str] = mapped_column(String(50), nullable=False)
    Fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)