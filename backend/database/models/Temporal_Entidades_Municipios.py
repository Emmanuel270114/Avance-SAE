from ..db_base import Base
from sqlalchemy import Integer, String, DateTime,func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class temporal_Entidades_Municipios(Base):
    __tablename__ = 'Entidades_Municipios'

    Id_Entidad_Municipio: Mapped[str] = mapped_column(String(50), primary_key=True, autoincrement=True)
    Id_Entidad: Mapped[str] = mapped_column(String(50), nullable=False)
    Id_Pais: Mapped[int] = mapped_column(Integer, nullable=False)
    Nombre_Entidad: Mapped[str] = mapped_column(String(100), nullable=False)
    Abreviatura_Entidad: Mapped[str] = mapped_column(String(10), nullable=False)
    Id_Municipio: Mapped[str] = mapped_column(String(50), nullable=False)
    Nombre_Municipio: Mapped[str] = mapped_column(String(100), nullable=False)
    Id_Localidad: Mapped[str] = mapped_column(String(50), nullable=True)
    Nombre_Localidad: Mapped[str] = mapped_column(String(200), nullable=True)
    