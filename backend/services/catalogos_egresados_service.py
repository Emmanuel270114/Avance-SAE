from sqlalchemy.orm import Session
from backend.database.models.CatBoleta import CatBoleta
from backend.database.models.CatGeneracion import CatGeneracion
from backend.database.models.CatSexo import CatSexo
from typing import List

def get_boletas_activas(db: Session) -> List[CatBoleta]:
    """
    Obtiene todas las boletas activas (Id_Estatus = 1)
    Ordenadas de forma descendente por el año de la boleta
    """
    try:
        boletas = db.query(CatBoleta).filter(
            CatBoleta.Id_Estatus == 1
        ).order_by(CatBoleta.Boleta.desc()).all()
        return boletas
    except Exception as e:
        print(f"Error al obtener boletas activas: {str(e)}")
        return []

def get_generaciones_activas(db: Session) -> List[CatGeneracion]:
    """
    Obtiene todas las generaciones activas (Id_Estatus = 1)
    Ordenadas de forma descendente por año
    """
    try:
        generaciones = db.query(CatGeneracion).filter(
            CatGeneracion.Id_Estatus == 1
        ).order_by(CatGeneracion.Generacion.desc()).all()
        return generaciones
    except Exception as e:
        print(f"Error al obtener generaciones activas: {str(e)}")
        return []

def get_sexos_activos(db: Session) -> List[CatSexo]:
    """
    Obtiene todos los sexos activos (Id_Estatus = 1)
    """
    try:
        sexos = db.query(CatSexo).filter(
            CatSexo.Id_Estatus == 1
        ).order_by(CatSexo.Id_Sexo).all()
        return sexos
    except Exception as e:
        print(f"Error al obtener sexos activos: {str(e)}")
        return []
