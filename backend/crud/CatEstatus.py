from backend.database.models.CatEstatus import CatEstatus
from backend.schemas.Estatus import EstatusBase

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import Optional, Sequence

############################__________________FUNCIONES CREATE____________________________############################
def create_Estatus(db: Session, Estatus_dict: EstatusBase) -> CatEstatus:
    new_Estatus = CatEstatus(**Estatus_dict.model_dump())
    db.add(new_Estatus)
    try:
        db.commit()
        db.refresh(new_Estatus)
    except IntegrityError:
        db.rollback()
        raise ValueError("El registro ya existe o los datos son invalidos")
    return(new_Estatus)

############################__________________FUNCIONES READ____________________________############################
def read_estatus_by_description(db: Session, name: str) -> Optional[CatEstatus]:
    try:
        stmt = select(CatEstatus).where(CatEstatus.Descripcion == name)
        return db.execute(stmt).scalars().first()
    except Exception as e:
        print(f"error en crud CatEstatus:{e}")
    return

def read_description_to_all_estatus(db: Session) -> Optional[Sequence[str]] :
    try:
        stmt = select(CatEstatus.Descripcion)
        return db.execute(stmt).scalars().all()
    except Exception as e:
        print(f"error en crud CatEstatus:{e}")

def update_estatus_by_name():
    return 0

def delete_Estatus_by_name():
    return 0

