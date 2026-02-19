from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class ProgramaModalidad(Base):
    __tablename__ = 'Programa_Modalidad'

    Id_Modalidad_Programa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Programa: Mapped[int] = mapped_column(Integer, nullable=False)
    Id_Modalidad: Mapped[int] = mapped_column(Integer, nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))