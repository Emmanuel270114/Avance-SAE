from ..db_base import Base
from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

class Temp_Usuarios(Base):
    __tablename__ = "Temp_Usuarios"

    Sigla: Mapped[str] = mapped_column(String(50), primary_key=True, index=True, nullable=False)
    Usuario: Mapped[str] = mapped_column(String(50), primary_key=True, index=True, nullable=False)
    Rol: Mapped[str] = mapped_column(String(50), nullable=False)
    Email: Mapped[str] = mapped_column(String(50), nullable=False)
    Nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    Paterno: Mapped[str] = mapped_column(String(50), nullable=False)
    Materno: Mapped[str] = mapped_column(String(50), nullable=False)
    Nivel: Mapped[str] = mapped_column(String(50), nullable=False)
    Formato: Mapped[str] = mapped_column(String(50), primary_key=True, nullable=False)