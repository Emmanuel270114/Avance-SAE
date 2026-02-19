from backend.database.models.CatRoles import CatRoles
from backend.schemas.Roles import RolesCreate

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import Optional, Sequence, Tuple

############################__________________FUNCIONES CREATE____________________________############################

def create_rol(db: Session, dict_rol:RolesCreate) -> CatRoles:
    new_rol = CatRoles(**dict_rol.model_dump())
    db.add(new_rol)
    try:
        db.commit()
        db.refresh(new_rol)
    except IntegrityError:
        db.rollback()
        raise ValueError("error en CRUD CatRoles")
    return new_rol


############################__________________FUNCIONES READ____________________________############################
def read_role_by_name(db: Session, name: str) -> Optional[CatRoles]:
    try:
        stmt = select(CatRoles).where(CatRoles.Rol == name)
        return db.execute(stmt).scalars().first()
    except Exception as e:
        raise ValueError(f"error en get_role_by_name crud: {e}")

def read_all_roles(db: Session) -> Sequence[CatRoles]:
    stmt = select(CatRoles).order_by(CatRoles.Rol)
    return db.execute(stmt).scalars().all()

def read_all_names_roles(db: Session) -> Sequence[str]: 
    stmt = select(CatRoles.Rol)
    result = db.execute(stmt).scalars().all()
    return result

def read_id_by_name(db: Session, name: str) -> Optional[int]:
    try:
        stmt = select(CatRoles.Id_Rol).where(CatRoles.Rol == name)
        result = db.execute(stmt).scalars().first()
        return result
    except Exception as e:
        print(f"error en get id by name crud:{e}")
        raise ValueError("error en crud get id by name")
    