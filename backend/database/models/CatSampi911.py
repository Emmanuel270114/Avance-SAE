from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatSapmi911(Base):
    __tablename__ = 'Cat_Sampi_911'

    Id_S911: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    S911: Mapped[str] = mapped_column(String(50), nullable=False)
    Descripcion: Mapped[str] = mapped_column(String(100), nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))