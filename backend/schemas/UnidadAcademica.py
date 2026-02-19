from pydantic import BaseModel

class UnidadAcademicaBase(BaseModel):
    Sigla: str
    Nombre: str

class UnidadAcademicaCreate(UnidadAcademicaBase):
    Director: str
    Clave: str
    Id_Estatus: int
    Id_Rama_Unidad: int

class UnidadAcademicaResponse(UnidadAcademicaBase):
    Id_Unidad_Academica: int

    model_config = {
        "from_attributes": True
    }

"""
Id_Unidad_Academica	int	NO	NULL
Sigla	nvarchar	NO	50
Nombre	nvarchar	NO	150
Clave	nvarchar	YES	50
Director	nvarchar	YES	150
Fecha_Inicio	date	NO	NULL
Fecha_Modificacion	date	NO	NULL
Fecha_Final	date	YES	NULL
Id_Estatus	int	NO	NULL
Imagen	varbinary	YES	-1
Id_Rama_Unidad	int	NO	NULL
"""