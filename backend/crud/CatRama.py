from backend.database.models.CatRama import CatRama
from backend.schemas.Rama import RamaCreate, RamaResponse

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

############################__________________FUNCIONES CREATE____________________________############################
def create_rama(db: Session, dict_rama:RamaCreate) -> CatRama:
    new_Rama = CatRama(**dict_rama.model_dump())
    db.add(new_Rama)
    try:
        db.commit()
        db.refresh(new_Rama)
    except IntegrityError:
        db.rollback()
        raise ValueError("La información introducida es incorrecta o ya existe")
    return new_Rama
