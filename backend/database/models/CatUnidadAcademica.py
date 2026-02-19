from ..db_base import Base

from sqlalchemy import Integer, String, ForeignKey, DateTime, func, BINARY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class CatUnidadAcademica(Base):
    __tablename__ = 'Cat_Unidad_Academica'

    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)    
    Sigla: Mapped[str] = mapped_column(String(50), nullable=False)
    Nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    Clave: Mapped[str] = mapped_column(nullable=True)
    Director: Mapped[str] = mapped_column(nullable=True)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    Fecha_Final: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))
    Imagen: Mapped[bytes] = mapped_column(BINARY,nullable=True)
    Id_Rama_Unidad: Mapped[int] = mapped_column(ForeignKey("Cat_Rama.Id_Rama"))