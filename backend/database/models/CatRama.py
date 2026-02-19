from ..db_base import Base

from sqlalchemy import String, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatRama(Base):
    __tablename__ = "Cat_Rama"

    Id_Rama: Mapped[int] = mapped_column(primary_key=True, index= True)
    Nombre_Rama: Mapped[str] = mapped_column(String(100), nullable=False)
    Nombre_Sigla: Mapped[str] = mapped_column(String(100), nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))
