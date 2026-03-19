from ..db_base import Base

from sqlalchemy import Integer,String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatFormatos(Base):
    __tablename__ = "Cat_Formatos"

    Id_Formato: Mapped[int] = mapped_column(primary_key=True, index=True)
    Formato: Mapped[str] = mapped_column(String(128), nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))