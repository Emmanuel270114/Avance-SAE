from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GeneracionBase(BaseModel):
    Generacion: str
    
class GeneracionCreate(GeneracionBase):
    pass

class GeneracionUpdate(GeneracionBase):
    pass

class GeneracionInDB(GeneracionBase):
    Id_Generacion: int
    Fecha_Inicio: datetime
    Fecha_Modificacion: datetime
    Fecha_Final: Optional[datetime] = None
    Id_Estatus: int
    
    class Config:
        from_attributes = True
