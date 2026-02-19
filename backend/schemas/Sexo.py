from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SexoBase(BaseModel):
    Sexo: str
    
class SexoCreate(SexoBase):
    pass

class SexoUpdate(SexoBase):
    pass

class SexoInDB(SexoBase):
    Id_Sexo: int
    Fecha_Inicio: datetime
    Fecha_Modificacion: datetime
    Fecha_Final: Optional[datetime] = None
    Id_Estatus: int
    
    class Config:
        from_attributes = True
