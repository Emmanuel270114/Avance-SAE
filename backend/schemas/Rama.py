from pydantic import BaseModel

class RamaBase(BaseModel):
    Nombre_Rama: str
    Nombre_Sigla: str

class RamaCreate(RamaBase):
    Id_Estatus: int

class RamaResponse(RamaBase):    
    Id_Rama: int

    model_config = {
        "from_attributes": True
    }


"""
Id_Rama	int	NO	NULL
Nombre_Rama	nvarchar	NO	100
Nombre_Sigla	nvarchar	NO	100
Fecha_Inicio	date	NO	NULL
Fecha_Modificacion	date	NO	NULL
Fecha_Final	date	YES	NULL
Id_Estatus	int	NO	NULL
"""