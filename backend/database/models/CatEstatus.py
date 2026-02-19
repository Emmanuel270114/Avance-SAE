from ..db_base import Base

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatEstatus(Base):
    __tablename__ = "Cat_Estatus"

    Id_Estatus: Mapped[int] = mapped_column(primary_key=True, index=True)
    Descripcion: Mapped[str] = mapped_column(String(128), nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)