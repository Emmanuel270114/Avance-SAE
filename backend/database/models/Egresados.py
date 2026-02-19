from re import M
from ..db_base import Base
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

class Egresados(Base):
    __tablename__ = 'Egresados'
    __table_args__ = {'extend_existing': True}  # Permitir tablas sin PK explícita

    Id_Periodo: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Periodos.Id_Periodo"), primary_key=True)
    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Unidad_Academica.Id_Unidad_Academica"), primary_key=True)
    Id_Programa: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Programas.Id_Programa"), nullable=False)
    Id_Rama: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Ramas.Id_Rama"), nullable=False)
    Id_Nivel: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Nivel.Id_Nivel"), nullable=False)
    Id_Modalidad: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Modalidad.Id_Modalidad"), nullable=False)
    Id_Grupo_Edad: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Grupo_Edad.Id_Grupo_Edad"), nullable=True)
    Id_Boleta: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Boleta.Id_Boleta"), nullable=True)
    Id_Generacion: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Generacion.Id_Generacion"), nullable=True)
    Id_Turno: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Turno.Id_Turno"), nullable=True)
    Id_Sexo: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Sexo.Id_Sexo"), nullable=False)
    Egresados:Mapped[int] = mapped_column(Integer, default=0, nullable=True)