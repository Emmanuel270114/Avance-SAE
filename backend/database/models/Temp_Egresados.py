from ..db_base import Base
from sqlalchemy import Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class Temp_Egresados(Base):
    __tablename__ = 'Temp_Egresados'

    Periodo: Mapped[str] = mapped_column(String(50), primary_key=True, index=True, nullable=False)
    Sigla: Mapped[str] = mapped_column(String(50), primary_key=True, index=True, nullable=False)
    Nombre_Programa: Mapped[str] = mapped_column(String(100), nullable=False)
    Nombre_Rama: Mapped[str] = mapped_column(String(50), nullable=False)
    Nivel: Mapped[str] = mapped_column(String(50), nullable=False)
    Modalidad: Mapped[str] = mapped_column(String(50), nullable=False)
    Grupo_Edad: Mapped[str] = mapped_column(String(50), nullable=False)  # Edad del egresado
    Boleta: Mapped[int] = mapped_column(nullable=False)
    Generacion: Mapped[str] = mapped_column(String(50), nullable=False)
    Turno: Mapped[str] = mapped_column(String(50), nullable=False)
    Sexo: Mapped[str] = mapped_column(String(50), nullable=False)
    Id_Semaforo: Mapped[int] = mapped_column(nullable=False)
    Egresados: Mapped[int] = mapped_column(nullable=True)
    