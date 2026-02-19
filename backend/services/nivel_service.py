from backend.database.models.CatProgramas import CatProgramas
from backend.database.models.ProgramaModalidad import ProgramaModalidad
from backend.database.models.UnidadProgramaModalidad import CatUnidadProgramaModalidad

from backend.database.models.CatNivel import CatNivel
from backend.schemas.Nivel import NivelResponse
from sqlalchemy.orm import Session

def get_all_niveles(db: Session, limit: int = 3) -> list[NivelResponse]:
    niveles = db.query(CatNivel).order_by(CatNivel.Id_Nivel).limit(limit).all()
    return [NivelResponse.model_validate(n, from_attributes=True) for n in niveles]


# --- NUEVA FUNCIÓN: obtener niveles por UA ---
def get_niveles_by_unidad_academica(db: Session, id_unidad_academica: int) -> list[NivelResponse]:
    # 1. Buscar todos los Unidad_Programa_Modalidad con ese id_unidad_academica
    upms = db.query(CatUnidadProgramaModalidad).filter_by(Id_Unidad_Academica=id_unidad_academica).all()
    niveles = set()
    for upm in upms:
        # 2. Seguir la relación: Unidad_Programa_Modalidad -> Programa_Modalidad
        pm = db.query(ProgramaModalidad).filter_by(Id_Modalidad_Programa=upm.Id_Modalidad_Programa).first()
        if not pm:
            continue
        # 3. Programa_Modalidad -> Cat_Programas
        prog = db.query(CatProgramas).filter_by(Id_Programa=pm.Id_Programa).first()
        if not prog:
            continue
        # 4. Cat_Programas -> Cat_Nivel
        nivel = db.query(CatNivel).filter_by(Id_Nivel=prog.Id_Nivel).first()
        if nivel:
            niveles.add(nivel)
    # Quitar duplicados y devolver como lista de esquemas
    return [NivelResponse.model_validate(n, from_attributes=True) for n in niveles]
