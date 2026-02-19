from pydantic import BaseModel, EmailStr
from typing import Optional

class UsuarioBase(BaseModel):
    Usuario: str
    Email: EmailStr

class UsuarioCreate(UsuarioBase):
    Id_Unidad_Academica: int
    Id_Rol: int
    Password: Optional[str] = None  # Opcional, se genera automáticamente si no se proporciona
    Id_Estatus: int
    Nombre: str
    Paterno: str
    Materno: str
    Id_Nivel: Optional[int] = None  # Permitir None para UAs sin niveles
    model_config = {
        "populate_by_name": True,
    }
    
class UsuarioResponse(UsuarioBase):
    Id_Usuario: int

    model_config = {
        "from_attributes": True
    }

class UsuarioLogin(UsuarioBase):
    Password: str