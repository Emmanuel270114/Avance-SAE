from ..db_base import Base
from sqlalchemy import Integer, DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatGeneracion(Base):
    __tablename__ = 'Cat_Generacion'

    Id_Generacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Generacion: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer)  # mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))