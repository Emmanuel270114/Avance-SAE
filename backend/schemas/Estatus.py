from pydantic import BaseModel

class EstatusBase(BaseModel):
    Descripcion: str    

class EstatusResponse(EstatusBase):
    Id_Estatus:int
    model_config = {
        "from_attributes": True
    }


"""
Id_Estatus	int	NO	NULL
Descripcion	nvarchar	NO	100
Fecha_Inicio	date	NO	NULL
Fecha_Modificacion	date	NO	NULL
Fecha_Final	date	YES	NULL
"""