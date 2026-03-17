from sqlalchemy.orm import Session
from backend.database.models.UnidadProgramaModalidad import CatUnidadProgramaModalidad
from backend.database.models.ProgramaModalidad import ProgramaModalidad
from backend.database.models.CatProgramas import CatProgramas
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica

def get_programas_por_unidad_academica(db: Session, id_unidad_academica: int):
    try:
        if not id_unidad_academica: return []
        # Convertir a int si viene como string
        if isinstance(id_unidad_academica, str) and id_unidad_academica.isdigit():
            id_u = int(id_unidad_academica)
        else:
            id_u = id_unidad_academica

        resultados = db.query(CatProgramas.Nombre_Programa)\
            .join(ProgramaModalidad, ProgramaModalidad.Id_Programa == CatProgramas.Id_Programa)\
            .join(CatUnidadProgramaModalidad, CatUnidadProgramaModalidad.Id_Modalidad_Programa == ProgramaModalidad.Id_Modalidad_Programa)\
            .filter(CatUnidadProgramaModalidad.Id_Unidad_Academica == id_u)\
            .distinct()\
            .all()
        return [r[0] for r in resultados]
    except Exception as e:
        print(f"Error al obtener programas por unidad: {str(e)}")
        return []

def get_unidades_con_niveles_asociados(db: Session):
    """
    Obtiene todas las unidades académicas junto con los niveles educativos (ids)
    que tienen asociados a través de sus programas.
    Retorna una lista de diccionarios con formato para el template.
    """
    try:
        # Join path: CatUnidadAcademica -> CatUnidadProgramaModalidad -> ProgramaModalidad -> CatProgramas -> (nivel)
        # Queremos columnas: Unidad.*, Programa.Id_Nivel
        
        # Consultamos las unidades que tienen programas activos
        results = db.query(CatUnidadAcademica, CatProgramas.Id_Nivel)\
            .join(CatUnidadProgramaModalidad, CatUnidadAcademica.Id_Unidad_Academica == CatUnidadProgramaModalidad.Id_Unidad_Academica)\
            .join(ProgramaModalidad, CatUnidadProgramaModalidad.Id_Modalidad_Programa == ProgramaModalidad.Id_Modalidad_Programa)\
            .join(CatProgramas, ProgramaModalidad.Id_Programa == CatProgramas.Id_Programa)\
            .filter(CatProgramas.Id_Estatus == 1)\
            .distinct()\
            .all()
            
        # Agrupamos los niveles por unidad
        unidades_map = {}
        for unidad, id_nivel in results:
            u_id = unidad.Id_Unidad_Academica
            if u_id not in unidades_map:
                # Inicializamos el diccionario de unidad
                unidades_map[u_id] = {
                    "Id_Unidad_Academica": unidad.Id_Unidad_Academica,
                    "Nombre_Unidad_Academica": unidad.Nombre, # Mapeamos al nombre correcto
                    "Sigla": unidad.Sigla,
                    "niveles": set()
                }
            
            # Agregamos el nivel al set (evita duplicados)
            unidades_map[u_id]["niveles"].add(id_nivel)
            
        # Convertimos a lista y formateamos los niveles para uso fácil en HTML/JS
        lista_unidades = []
        for data in unidades_map.values():
            # Convertimos el set de niveles a un string separado por comas: "1,2,3"
            data["niveles_str"] = ",".join(map(str, sorted(list(data["niveles"]))))
            lista_unidades.append(data)
            
        # Ordenar alfabéticamente por nombre
        lista_unidades.sort(key=lambda x: x["Nombre_Unidad_Academica"])
        
        return lista_unidades

    except Exception as e:
        print(f"Error al obtener unidades con niveles: {str(e)}")
        return []