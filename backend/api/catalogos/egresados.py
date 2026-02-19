from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.services.catalogos_egresados_service import (
    get_boletas_activas,
    get_generaciones_activas,
    get_sexos_activos
)
from backend.schemas.Boleta import BoletaInDB
from backend.schemas.Generacion import GeneracionInDB
from backend.schemas.Sexo import SexoInDB
from typing import List

router = APIRouter()

@router.get("/boletas", response_model=List[BoletaInDB])
async def obtener_boletas(db: Session = Depends(get_db)):
    """
    Obtiene todas las boletas activas ordenadas descendentemente
    """
    boletas = get_boletas_activas(db)
    return boletas

@router.get("/generaciones", response_model=List[GeneracionInDB])
async def obtener_generaciones(db: Session = Depends(get_db)):
    """
    Obtiene todas las generaciones activas ordenadas descendentemente
    """
    generaciones = get_generaciones_activas(db)
    return generaciones

@router.get("/sexos", response_model=List[SexoInDB])
async def obtener_sexos(db: Session = Depends(get_db)):
    """
    Obtiene todos los sexos activos (Hombre, Mujer)
    """
    sexos = get_sexos_activos(db)
    return sexos
