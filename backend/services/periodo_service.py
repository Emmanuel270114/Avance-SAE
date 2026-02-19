"""
Servicio para gestionar operaciones relacionadas con Periodos.
"""
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from backend.database.models.CatPeriodo import CatPeriodo


def get_ultimo_periodo(db: Session) -> Tuple[Optional[int], Optional[str]]:
    """
    Obtiene el último periodo creado en la base de datos.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Tuple[Optional[int], Optional[str]]: (Id_Periodo, Periodo literal)
        Retorna (None, None) si no hay periodos en la base de datos
    
    Ejemplo:
        >>> id_periodo, periodo_literal = get_ultimo_periodo(db)
        >>> print(id_periodo, periodo_literal)
        7, '2025-2026/1'
    """
    try:
        # Obtener el último periodo ordenado por Id_Periodo descendente
        ultimo_periodo = db.query(CatPeriodo).order_by(
            CatPeriodo.Id_Periodo.desc()
        ).first()
        
        if ultimo_periodo:
            return ultimo_periodo.Id_Periodo, ultimo_periodo.Periodo
        
        # Si no hay periodos, retornar None
        return None, None
        
    except Exception as e:
        print(f"Error al obtener último periodo: {e}")
        return None, None


def get_periodo_activo(db: Session) -> Tuple[Optional[int], Optional[str]]:

    """
    Obtiene el periodo activo (Id_Estatus = 1).
    Si hay múltiples activos, retorna el más reciente.
    Si no hay activos, retorna el último periodo creado.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Tuple[Optional[int], Optional[str]]: (Id_Periodo, Periodo literal)
    """
    try:
        # Intentar obtener periodo activo
        periodo_activo = db.query(CatPeriodo).filter(
            CatPeriodo.Id_Estatus == 1
        ).order_by(
            CatPeriodo.Id_Periodo.desc()
        ).first()
        
        if periodo_activo:
            return periodo_activo.Id_Periodo, periodo_activo.Periodo
        
        # Si no hay periodo activo, usar el último creado
        return get_ultimo_periodo(db)
        
    except Exception as e:
        print(f"Error al obtener periodo activo: {e}")
        return None, None


def get_periodo_por_id(db: Session, id_periodo: int) -> Optional[str]:
    """
    Obtiene el periodo literal por su ID.
    
    Args:
        db: Sesión de base de datos
        id_periodo: ID del periodo a buscar
        
    Returns:
        Optional[str]: Periodo literal o None si no se encuentra
    """
    try:
        periodo = db.query(CatPeriodo).filter(
            CatPeriodo.Id_Periodo == id_periodo
        ).first()
        
        return periodo.Periodo if periodo else None
        
    except Exception as e:
        print(f"Error al obtener periodo por ID: {e}")
        return None

def get_periodo_anterior_al_ultimo(db: Session) -> Tuple[Optional[int], Optional[str]]:
    """
    Obtiene el penúltimo periodo creado en la base de datos (offset 1 del último).
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Tuple[Optional[int], Optional[str]]: (Id_Periodo, Periodo literal)
        Retorna (None, None) si hay menos de 2 periodos en la base de datos.
    """
    try:
        # Ordenamos descendente y saltamos el primero (el último) para tomar el siguiente
        periodo_anterior = db.query(CatPeriodo).order_by(
            CatPeriodo.Id_Periodo.desc()
        ).offset(1).first()
        
        if periodo_anterior:
            return periodo_anterior.Id_Periodo, periodo_anterior.Periodo
        
        # Si no existe un penúltimo (solo hay 0 o 1 registros), retornar None
        return None, None
        
    except Exception as e:
        print(f"Error al obtener el periodo anterior al último: {e}")
        return None, None