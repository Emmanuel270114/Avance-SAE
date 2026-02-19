from pydantic import BaseModel


class RolesBase(BaseModel):
    Rol: str
    Descripcion: str


class RolesCreate(RolesBase):
    Id_Estatus: int


class RolesResponse(RolesBase):
    Id_Rol: int

    model_config = {
        "from_attributes": True
    }

"""
Id_Rol	int	NO	NULL
Nombre	nvarchar	NO	50
Descripcion	nvarchar	NO	100
Fecha_Inicio	date	NO	NULL
Fecha_Modificacion	date	NO	NULL
Fecha_Final	date	YES	NULL
Id_Estatus	int	NO	NULL
"""