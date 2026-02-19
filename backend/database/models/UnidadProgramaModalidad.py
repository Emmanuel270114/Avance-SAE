from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatUnidadProgramaModalidad(Base):
    __tablename__ = 'Unidad_Programa_Modalidad'
    
    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Modalidad_Programa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))