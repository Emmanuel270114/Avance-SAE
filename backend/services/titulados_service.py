from sqlalchemy.orm import Session
from backend.crud.ConsultaTitulados import get_titulados
#from backend.schemas.titulados import TituladoSchema
from typing import List, Dict, Any


def obtener_titulados(
    db: Session,
    unidad_academica,
    periodo,
    nivel,
    usuario,
    host
) :
    """
    Capa de servicio: valida parámetros y llama al crud.
    Aquí puedes agregar lógica adicional, filtros, transformaciones, etc.
    """
    if not unidad_academica or not periodo or not nivel or not usuario:
        raise ValueError("Todos los parámetros son obligatorios.")

    datos = get_titulados(
        db=db,
        unidad_academica=unidad_academica,
        periodo=periodo,
        nivel=nivel,
        usuario=usuario,
        host=host
    )

    if datos:

        contexto = {
            "Periodo" : datos[0].get("Periodo"),
            "Sigla" : datos[0].get("Sigla"),
        }

        filas = [{
            "Nombre_Programa": row["Nombre_Programa"],
            "Nombre_Rama": row["Nombre_Rama"],
            "Nivel": row["Nivel"],
            "Modalidad": row["Modalidad"],
            "Grupo_Edad": row["Grupo_Edad"],
            "Boleta": row["Boleta"],
            "Tipo_Titulacion": row["Tipo_Titulacion"],
            "Turno": row["Turno"],
            "Sexo": row["Sexo"],
            "Id_Semaforo": row["Id_Semaforo"],
            "Titulados": row["Titulados"],
        }
        for row in datos
        ]
    else:
        contexto = {}
        filas = []

    return contexto, filas