from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatProgramas(Base):
    __tablename__ = 'Cat_Programas'

    Id_Programa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Nombre_Programa: Mapped[str] = mapped_column(String(100), nullable=False)
    Id_Nivel: Mapped[int] = mapped_column(Integer, nullable=False) #mapped_column(ForeignKey("Cat_Nivel.Id_Nivel"))
    Id_Rama_Programa: Mapped[int] = mapped_column(Integer, nullable=False) #mapped_column(ForeignKey("Cat_Rama.Id_Rama"))
    Id_Semestre: Mapped[int] = mapped_column(Integer, nullable=False) #mapped_column(ForeignKey("Cat_Semestre.Id_Semestre"))
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))