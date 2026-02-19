from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class CatDomicilios(Base):
    __tablename__ = 'Cat_Domicilios'

    Id_Domicilio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Entidad_Municipio: Mapped[int] = mapped_column(Integer, nullable=False) #mapped_column(ForeignKey("Cat_Entidad_Municipio.Id_Entidad_Municipio")) 
    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer, nullable=False) #mapped_column(ForeignKey("Cat_Unidad_Academica.Id_Unidad_Academica"))
    Calle: Mapped[str] = mapped_column(String(255), nullable=False)
    Numero: Mapped[str] = mapped_column(String(50), nullable=False)
    Colonia: Mapped[str] = mapped_column(String(255), nullable=False)
    CP: Mapped[str] = mapped_column(String(10), nullable=False)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),  nullable=False)
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))