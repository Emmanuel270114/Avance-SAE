from ..db_base import Base
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

class Matricula(Base):
    __tablename__ = 'Matricula'
    __table_args__ = {'extend_existing': True}  # Permitir tablas sin PK explícita

    Id_Periodo: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Periodos.Id_Periodo"), primary_key=True)
    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Unidad_Academica.Id_Unidad_Academica"), primary_key=True)
    Id_Programa: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Programas.Id_Programa"), nullable=False)
    Id_Rama: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Ramas.Id_Rama"), nullable=False)
    Id_Nivel: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Nivel.Id_Nivel"), nullable=False)
    Id_Modalidad: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Modalidad.Id_Modalidad"), nullable=False)
    Id_Turno: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Turno.Id_Turno"), nullable=False)
    Id_Semestre: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Semestre.Id_Semestre"), nullable=False)
    Id_Grupo_Edad: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Grupo_Edad.Id_Grupo_Edad"), nullable=False)
    Id_Tipo_Ingreso: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Tipo_Ingreso.Id_Tipo_Ingreso"), nullable=False)
    Id_Sexo: Mapped[int] = mapped_column(Integer, ForeignKey("Cat_Sexo.Id_Sexo"), nullable=False)
    Matricula: Mapped[int] = mapped_column(Integer, default=0, nullable=False)