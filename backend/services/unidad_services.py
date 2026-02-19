from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.crud.CatUnidadAcademica import create_unidad, read_all_unidades
from backend.schemas.UnidadAcademica import UnidadAcademicaCreate, UnidadAcademicaResponse
from backend.schemas.UnidadAcademica import UnidadAcademicaResponse

from sqlalchemy.orm import Session

def unidad_already_exists(db: Session):
    return 0

def get_all_units(db: Session) -> list[UnidadAcademicaResponse]:
    unidades = read_all_unidades(db)
    return [UnidadAcademicaResponse.model_validate(u) for u in unidades]