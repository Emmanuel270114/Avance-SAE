from ..db_base import Base
from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

class Usuario(Base):
    __tablename__ = "Usuarios"

    Id_Usuario: Mapped[int] = mapped_column(primary_key=True, index=True)
    Id_Unidad_Academica: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Unidad_Academica.Id_Unidad_Academica"))
    Id_Rol: Mapped[int] = mapped_column(Integer)#mapped_column(ForeignKey("Cat_Roles.Id_Rol"))
    Usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    Password: Mapped[str] = mapped_column("Contrasena", String(2000), nullable=False)
    Email: Mapped[str] = mapped_column(String(255), unique=True)
    Fecha_Inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    Fecha_Modificacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    Fecha_Final: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    Id_Estatus: Mapped[int] = mapped_column(Integer) #mapped_column(ForeignKey("Cat_Estatus.Id_Estatus"))
    Nombre: Mapped[str] = mapped_column(String(50), nullable=True)
    Paterno: Mapped[str] = mapped_column(String(50), nullable=True)
    Materno: Mapped[str] = mapped_column(String(50), nullable=True)
    Id_Nivel: Mapped[int] = mapped_column(Integer,nullable=True) #mapped_column(ForeignKey("Cat_Nivel.Id_Nivel"))
    
