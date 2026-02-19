from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BoletaBase(BaseModel):
    Boleta: int
    
class BoletaCreate(BoletaBase):
    pass

class BoletaUpdate(BoletaBase):
    pass

class BoletaInDB(BoletaBase):
    Id_Boleta: int
    Fecha_Inicio: datetime
    Fecha_Modificacion: datetime
    Fecha_Final: Optional[datetime] = None
    Id_Estatus: int
    
    class Config:
        from_attributes = True
