from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import List, Dict, Any, Tuple, Optional
from fastapi import HTTPException
from datetime import datetime
import time

from backend.core.templates import templates
from backend.core.auth import get_current_session
from backend.database.connection import get_db
from backend.database.models.Egresados import Egresados
from backend.database.models.CatPeriodo import CatPeriodo as Periodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica as Unidad_Academica
from backend.database.models.CatNivel import CatNivel as Nivel
from backend.database.models.CatProgramas import CatProgramas as Programas
from backend.database.models.CatModalidad import CatModalidad as Modalidad
from backend.database.models.CatTurno import CatTurno as Turno
from backend.database.models.CatBoleta import CatBoleta as Boleta
from backend.database.models.CatGeneracion import CatGeneracion as Generacion
from backend.database.models.CatSexo import CatSexo as Sexo
from backend.database.models.CatRama import CatRama as Rama
from backend.database.models.CatSemaforo import CatSemaforo
from backend.database.models.SemaforoUnidadAcademica import SemaforoUnidadAcademica
from backend.database.models.SemaforoSemestreUnidadAcademica import SemaforoSemestreUnidadAcademica
from backend.database.models.ProgramaModalidad import ProgramaModalidad
from backend.database.models.UnidadProgramaModalidad import CatUnidadProgramaModalidad
from backend.database.models.Validacion import Validacion
from backend.utils.request import get_request_host
from backend.database.models.Temp_Egresados import Temp_Egresados
from backend.database.models.CatRoles import CatRoles
from backend.services.periodo_service import get_periodo_activo, get_ultimo_periodo, get_periodo_anterior_al_ultimo

router = APIRouter()


def extract_unique_values_egresados(rows_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extraer valores únicos del SP de egresados para boletas, generaciones, turnos, etc.
    
    Args:
        rows_list: Lista de filas del SP como diccionarios
        
    Returns:
        Dict con estructuras únicas extraídas del SP
    """
    programas_set = set()
    modalidades_set = set()
    boletas_set = set()
    generaciones_set = set()
    turnos_set = set()
    edades_set = set()
    sexos_set = set()
    
    # Mapeo de Programa -> Modalidades
    programa_modalidades = {}
    
    for row in rows_list:
        programa_nombre = None
        modalidad_nombre = None
        
        if 'Nombre_Programa' in row and row['Nombre_Programa']:
            programa_nombre = str(row['Nombre_Programa'])
            programas_set.add(programa_nombre)
        
        if 'Modalidad' in row and row['Modalidad']:
            modalidad_nombre = str(row['Modalidad'])
            modalidades_set.add(modalidad_nombre)
        
        # Crear mapeo programa -> modalidades
        if programa_nombre and modalidad_nombre:
            if programa_nombre not in programa_modalidades:
                programa_modalidades[programa_nombre] = set()
            programa_modalidades[programa_nombre].add(modalidad_nombre)
        
        if 'Boleta' in row and row['Boleta']:
            boletas_set.add(str(row['Boleta']))
        
        if 'Generacion' in row and row['Generacion']:
            generaciones_set.add(str(row['Generacion']))
        
        if 'Turno' in row and row['Turno']:
            turnos_set.add(str(row['Turno']))
        
        # Intentar extraer edad de diferentes columnas posibles
        # Las edades pueden venir en formatos: "<=18", "19", "35-40", ">=65", etc.
        edad_valor = None
        if 'Grupo_Edad' in row and row['Grupo_Edad'] is not None:
            edad_valor = row['Grupo_Edad']
        elif 'Edad' in row and row['Edad'] is not None:
            edad_valor = row['Edad']
        
        if edad_valor is not None:
            # Guardar el valor tal como viene (string) sin intentar convertir
            # Esto permite rangos como "35-40", comparadores como "<=18", ">=65", y números simples
            edad_str = str(edad_valor).strip()
            if edad_str and edad_str != 'None' and edad_str != '':
                edades_set.add(edad_str)
        
        if 'Sexo' in row and row['Sexo']:
            sexos_set.add(str(row['Sexo']))
    
    # Convertir sets de modalidades a listas ordenadas
    programa_modalidades_list = {prog: sorted(list(mods)) for prog, mods in programa_modalidades.items()}
    
    # Ordenar edades por valor numérico, ignorando símbolos de comparación
    def ordenar_edades(edad_str):
        """Función para ordenar edades extrayendo el número principal"""
        import re
        edad_str = str(edad_str).strip()
        
        # Extraer todos los números de la cadena
        numeros = re.findall(r'\d+', edad_str)
        
        if not numeros:
            return (999, edad_str)  # Sin números, al final
        
        # Usar el primer número encontrado para ordenar
        numero_principal = int(numeros[0])
        return (numero_principal, edad_str)
    
    edades_ordenadas = sorted(list(edades_set), key=ordenar_edades)
    
    return {
        'programas': sorted(list(programas_set)),
        'modalidades': sorted(list(modalidades_set)),
        'programa_modalidades': programa_modalidades_list,  # Nuevo mapeo
        'boletas': sorted(list(boletas_set), reverse=True),  # Descendente
        'generaciones': sorted(list(generaciones_set), reverse=True),  # Descendente
        'turnos': sorted(list(turnos_set)),
        'edades': edades_ordenadas,  # Ordenadas por lógica especial
        'sexos': sorted(list(sexos_set))
    }


def execute_egresados_sp(
    db: Session,
    unidad_sigla: str,
    periodo_literal: str,
    nivel_nombre: str,
    usuario: str = 'sistema',
    host: str = 'localhost'
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Ejecuta el SP_Consulta_Egresados_Unidad_Academica
    
    Returns:
        Tuple[List[Dict], Optional[str]]: (datos, nota_rechazo)
    """
    try:
        # Log de parámetros que se enviarán al SP
        print(f"🔍 Ejecutando SP con parámetros:")
        print(f"   @UUnidad_Academica = '{unidad_sigla}'")
        print(f"   @Pperiodo = '{periodo_literal}'")
        print(f"   @NNivel = '{nivel_nombre}'")
        print(f"   @UUsuario = '{usuario}'")
        print(f"   @HHost = '{host}'")
        
        sp_call = text("""
            EXEC SP_Consulta_Egresados_Unidad_Academica 
                @UUnidad_Academica = :unidad,
                @Pperiodo = :periodo,
                @NNivel = :nivel,
                @UUsuario = :usuario,
                @HHost = :host
        """)
        
        result = db.execute(sp_call, {
            'unidad': unidad_sigla,
            'periodo': periodo_literal,
            'nivel': nivel_nombre,
            'usuario': usuario,
            'host': host
        })
        
        # Primer resultset: datos de egresados
        rows = result.fetchall()
        columns = result.keys()
        
        egresados_data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            egresados_data.append(row_dict)
        
        # Intentar obtener nota de rechazo (segundo resultset)
        nota_rechazo = None
        try:
            # Para SQL Server, usar el cursor raw si está disponible
            if hasattr(result, 'cursor') and hasattr(result.cursor, 'nextset'):
                if result.cursor.nextset():
                    nota_rows = result.cursor.fetchall()
                    if nota_rows and len(nota_rows) > 0:
                        nota_rechazo = nota_rows[0][0] if nota_rows[0] else None
        except Exception as e_nextset:
            print(f"⚠️ No se pudo obtener segundo resultset (nota rechazo): {str(e_nextset)}")
        
        return egresados_data, nota_rechazo
        
    except Exception as e:
        print(f"❌ Error ejecutando SP de egresados: {str(e)}")
        import traceback
        traceback.print_exc()
        return [], None


@router.get('/consulta')
async def captura_egresados_sp_view(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint principal para la visualización/captura de egresados usando EXCLUSIVAMENTE Stored Procedures.
    Accesible para:
    - Rol 'Capturista' (ID 3): Captura y validación de datos
    - Roles con ID 4, 5, 6, 7, 8: Solo visualización y validación/rechazo (sin edición)
    TODA la información viene del SP, NO de los modelos ORM.
    """
    # Obtener datos del usuario logueado desde las cookies
    id_unidad_academica = int(sess.id_unidad_academica)
    
    # Manejar id_nivel que puede ser None para usuarios sin nivel (ej: directores)
    id_nivel = int(getattr(sess, 'id_nivel', 0) or 0)
    
    id_rol = int(sess.id_rol)
    nombre_rol = sess.nombre_rol
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Validar que el usuario tenga uno de los roles permitidos
    roles_permitidos = [1, 3, 4, 5, 6, 7, 8, 9]  #1=Admin, 3=Capturista, 4-9=Roles de validación/rechazo
    if id_rol not in roles_permitidos:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Acceso denegado: Su rol ({nombre_rol}) no tiene permisos para acceder a esta funcionalidad.",
            "redirect_url": "/mod_principal/"
        })
    
    # Determinar el modo de vista según el rol
    es_capturista = (id_rol == 3)
    es_validador = (id_rol in [4, 5, 6, 7, 8, 9])  # Roles de validación/rechazo
    es_rol_director = (id_rol in [4, 5])  # Roles 4-5: Subdirector/Director - Consultan su UA con selector de nivel
    es_rol_superior = (id_rol in [6, 7, 8, 9])  # Roles 6-9: Pueden ver todas las UAs
    modo_vista = "captura" if es_capturista else "validacion"

    print(f"\n{'='*60}")
    print(f"CARGANDO VISTA DE EGRESADOS - TODO DESDE SP")
    print(f"Usuario: {nombre_completo}")
    print(f"Rol: {nombre_rol} (ID: {id_rol})")
    print(f"Modo de vista: {modo_vista.upper()}")
    print(f"Es rol superior (4-9): {es_rol_superior}")
    print(f"ID Unidad Académica: {id_unidad_academica}")
    print(f"ID Nivel: {id_nivel}")
    print(f"{'='*60}")

    # === VERIFICAR ACCESO BASADO EN SEMÁFORO (FORMATO 3 = EGRESADOS) ===
    # Comentado: Ahora roles 4-9 todos pueden ver el selector y elegir qué consultar
    # if id_rol in [4, 5] and not es_rol_superior:
    #     try:
    #         periodo_id, periodo_literal = get_ultimo_periodo(db)
    #         ...
    #     except Exception as e:
    #         print(f"Error al verificar semáforo: {str(e)}")

    # === OBTENER PERIODO POR DEFECTO ===
    try:
        periodo_id, periodo_literal = get_ultimo_periodo(db)
        if not periodo_id or not periodo_literal:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_message": "No hay un periodo activo configurado en el sistema.",
                "redirect_url": "/mod_principal/"
            })
        
        periodo_default_id = periodo_id
        periodo_default_literal = periodo_literal
        print(f"📅 Periodo por defecto: {periodo_default_literal} (ID: {periodo_default_id})")
    except Exception as e:
        print(f"❌ Error al obtener periodo: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Error al cargar el periodo: {str(e)}",
            "redirect_url": "/mod_principal/"
        })

    # === OBTENER INFORMACIÓN DE UNIDAD ACADÉMICA ===
    unidad_actual = None
    if (not es_rol_superior or es_rol_director) and id_unidad_academica > 0:
        unidad_actual = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        print(f"🏫 Unidad Académica: {unidad_actual.Nombre if unidad_actual else 'No definida'}")
        
        if es_rol_director:
            print(f"👔 Rol Director (4-5): UA fija = {unidad_actual.Nombre if unidad_actual else 'N/A'}")

    # === PARA ROLES DIRECTORES (4-5) Y SUPERIORES (6-9): Cargar niveles y UAs según corresponda ===
    unidades_disponibles = []
    niveles_disponibles = []
    nivel_a_uas_json = "{}"
    periodos = []
    
    # Roles 4-5: Solo cargar niveles de su UA
    if es_rol_director:
        # Obtener todos los periodos
        periodos = db.query(Periodo).filter(Periodo.Id_Estatus == 1).order_by(Periodo.Id_Periodo.desc()).all()
        
        # Obtener niveles disponibles para esta UA desde SemaforoUnidadAcademica
        if unidad_actual:
            niveles_ua = db.query(Nivel).join(
                SemaforoUnidadAcademica,
                SemaforoUnidadAcademica.Id_Nivel == Nivel.Id_Nivel
            ).filter(
                SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoUnidadAcademica.Id_Formato == 3,  # Formato 3 = Egresados
                Nivel.Id_Estatus == 1
            ).distinct().all()
            
            niveles_disponibles = [{"Id_Nivel": n.Id_Nivel, "Nivel": n.Nivel} for n in niveles_ua]
            print(f"👔 Niveles disponibles para UA {id_unidad_academica}: {[n['Nivel'] for n in niveles_disponibles]}")
    
    # Roles 6-9: Cargar todo
    elif es_rol_superior:
        # Obtener todos los periodos
        periodos = db.query(Periodo).filter(Periodo.Id_Estatus == 1).order_by(Periodo.Id_Periodo.desc()).all()
        
        # Obtener todos los niveles activos
        niveles_db = db.query(Nivel).filter(Nivel.Id_Estatus == 1).all()
        niveles_disponibles = [{"Id_Nivel": n.Id_Nivel, "Nivel": n.Nivel} for n in niveles_db]
        
        # Obtener todas las unidades académicas activas
        unidades_db = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Estatus == 1
        ).order_by(Unidad_Academica.Nombre).all()
        unidades_disponibles = [{"Id_Unidad_Academica": u.Id_Unidad_Academica, "Nombre": u.Nombre, "Sigla": u.Sigla} for u in unidades_db]
        
        # Obtener relaciones Nivel-UA desde SemaforoUnidadAcademica (Formato 3 = Egresados)
        relaciones_nivel_ua = db.query(
            SemaforoUnidadAcademica.Id_Nivel,
            SemaforoUnidadAcademica.Id_Unidad_Academica
        ).filter(
            SemaforoUnidadAcademica.Id_Formato == 3  # Formato 3 = Egresados
        ).distinct().all()
        
        # Mapear Nivel a UAs (para que al seleccionar Nivel se muestren sus UAs)
        nivel_a_uas = {}
        for rel in relaciones_nivel_ua:
            id_nivel_rel = rel.Id_Nivel
            id_ua = rel.Id_Unidad_Academica
            
            if id_nivel_rel not in nivel_a_uas:
                nivel_a_uas[id_nivel_rel] = []
            if id_ua not in nivel_a_uas[id_nivel_rel]:
                nivel_a_uas[id_nivel_rel].append(id_ua)
        
        nivel_a_uas_json = json.dumps(nivel_a_uas)
        print(f"📊 Roles superiores: {len(unidades_disponibles)} UAs disponibles")
        print(f"📊 Relaciones Nivel-UA: {len(relaciones_nivel_ua)} relaciones")
        print(f"📊 Mapeo Nivel->UAs: {nivel_a_uas}")

    # === OBTENER METADATOS DEL SP PARA TODOS LOS ROLES (incluye mapeo programa→modalidad) ===
    programas_formatted = []
    modalidades_formatted = []
    boletas_formatted = []
    generaciones_formatted = []
    turnos_formatted = []
    edades_formatted = []
    sexos_formatted = []
    programa_a_modalidades_json = "{}"  # Mapeo programa->modalidades para filtrado dinámico
    
    # Para roles 4-9 (directores y superiores): cargar TODAS las modalidades y programas sin ejecutar SP
    if es_rol_director or es_rol_superior:
        try:
            # Obtener TODAS las modalidades activas (sin filtrar por UA ni programa)
            modalidades_db = db.query(Modalidad).filter(
                Modalidad.Id_Estatus == 1
            ).all()
            modalidades_formatted = [{"id": m.Id_Modalidad, "nombre": m.Modalidad} for m in modalidades_db]
            print(f"🎓 Modalidades disponibles para roles 4-9: {len(modalidades_formatted)}")
            
            # Obtener TODOS los programas activos de todos los niveles
            programas_db = db.query(Programas).filter(
                Programas.Id_Estatus == 1
            ).all()
            programas_formatted = [{"id": p.Id_Programa, "nombre": p.Nombre_Programa} for p in programas_db]
            print(f"📚 Programas disponibles para roles 4-9: {len(programas_formatted)}")
            
            # Crear mapeo Programa->Modalidades desde ProgramaModalidad
            # Esto asegura que el filtrado dinámico funcione cuando el usuario seleccione UA y consulte
            from backend.database.models.ProgramaModalidad import ProgramaModalidad
            relaciones = db.query(ProgramaModalidad).filter(
                ProgramaModalidad.Id_Estatus == 1
            ).all()
            
            programa_a_modalidades = {}
            for rel in relaciones:
                if rel.Id_Programa not in programa_a_modalidades:
                    programa_a_modalidades[rel.Id_Programa] = []
                if rel.Id_Modalidad not in programa_a_modalidades[rel.Id_Programa]:
                    programa_a_modalidades[rel.Id_Programa].append(rel.Id_Modalidad)
            
            programa_a_modalidades_json = json.dumps(programa_a_modalidades)
            print(f"🔗 Mapeo Programa->Modalidad para roles 4-9: {len(programa_a_modalidades)} programas")
            
            # Para roles 4-9, NO se cargan turnos, boletas, generaciones, edades
            # Estos filtros están ocultos para roles 4-9 (solo los usa el capturista)
            # Si en el futuro se necesitan, deberían venir del SP como lo hace el rol 3
            boletas_formatted = []
            generaciones_formatted = []
            turnos_formatted = []
            sexos_formatted = []
            edades_formatted = []
            
            print(f"✅ Metadatos cargados para roles 4-9 SIN ejecutar SP")
            print(f"⏳ El SP se ejecutará cuando el usuario haga clic en 'Consultar Egresados'")
            
        except Exception as e:
            print(f"❌ Error al cargar metadatos para roles 4-9: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Para rol 3 (capturista) ÚNICAMENTE: cargar desde el SP de su UA específica
    elif es_capturista and id_nivel > 0 and id_unidad_academica > 0:
        print(f"🔄 Rol Capturista detectado - Ejecutando SP inmediatamente para cargar datos iniciales...")
        try:
            # Obtener datos necesarios para el SP
            nivel = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
            nivel_nombre = nivel.Nivel if nivel else ""
            
            # Para egresados, usar el periodo actual (el último/default)
            periodo_para_sp = periodo_default_literal
            print(f"📅 Usando periodo para SP de egresados: {periodo_para_sp}")

            # Ejecutar SP para obtener metadatos
            resultados_sp, _ = execute_egresados_sp(
                db=db,
                unidad_sigla=unidad_actual.Sigla if unidad_actual else "",
                periodo_literal=periodo_para_sp,
                nivel_nombre=nivel_nombre,
                usuario=nombre_completo,
                host=get_request_host(request)
            )
            
            if resultados_sp:
                # Extraer valores únicos del SP
                valores_unicos = extract_unique_values_egresados(resultados_sp)
                
                print(f"📊 METADATOS EXTRAÍDOS DEL SP:")
                print(f"   Programas: {valores_unicos.get('programas', [])}")
                print(f"   Modalidades: {valores_unicos.get('modalidades', [])}")
                print(f"   Boletas: {valores_unicos.get('boletas', [])}")
                print(f"   Generaciones: {valores_unicos.get('generaciones', [])}")
                print(f"   Turnos: {valores_unicos.get('turnos', [])}")
                print(f"   Edades: {valores_unicos.get('edades', [])}")
                print(f"   Sexos: {valores_unicos.get('sexos', [])}")
                print(f"   Mapeo Programa->Modalidades: {valores_unicos.get('programa_modalidades', {})}")
                
                # Mapear Programas
                programas_sp = valores_unicos.get('programas', [])
                if programas_sp:
                    programas_db = db.query(Programas).filter(
                        Programas.Nombre_Programa.in_(programas_sp),
                        Programas.Id_Nivel == id_nivel,
                        Programas.Id_Estatus == 1
                    ).all()
                    programas_formatted = [{"id": p.Id_Programa, "nombre": p.Nombre_Programa} for p in programas_db]
                    print(f"📚 Programas mapeados ({len(programas_formatted)}): {[p['nombre'] for p in programas_formatted]}")
                
                # Mapear Modalidades
                modalidades_sp = valores_unicos.get('modalidades', [])
                if modalidades_sp:
                    modalidades_db = db.query(Modalidad).filter(
                        Modalidad.Modalidad.in_(modalidades_sp),
                        Modalidad.Id_Estatus == 1
                    ).all()
                    modalidades_formatted = [{"id": m.Id_Modalidad, "nombre": m.Modalidad} for m in modalidades_db]
                    print(f"🎓 Modalidades mapeadas ({len(modalidades_formatted)}): {[m['nombre'] for m in modalidades_formatted]}")
                
                # Mapear Boletas
                boletas_sp = valores_unicos.get('boletas', [])
                if boletas_sp:
                    boletas_db = db.query(Boleta).filter(
                        Boleta.Boleta.in_(boletas_sp),
                        Boleta.Id_Estatus == 1
                    ).order_by(Boleta.Boleta.desc()).all()
                    boletas_formatted = [{"id": b.Id_Boleta, "nombre": b.Boleta} for b in boletas_db]
                    print(f"📋 Boletas mapeadas ({len(boletas_formatted)}): {[b['nombre'] for b in boletas_formatted]}")
                
                # Mapear Generaciones
                generaciones_sp = valores_unicos.get('generaciones', [])
                if generaciones_sp:
                    generaciones_db = db.query(Generacion).filter(
                        Generacion.Generacion.in_(generaciones_sp),
                        Generacion.Id_Estatus == 1
                    ).order_by(Generacion.Generacion.desc()).all()
                    generaciones_formatted = [{"id": g.Id_Generacion, "nombre": g.Generacion} for g in generaciones_db]
                    print(f"🎓 Generaciones mapeadas ({len(generaciones_formatted)}): {[g['nombre'] for g in generaciones_formatted]}")
                
                # Mapear Turnos
                turnos_sp = valores_unicos.get('turnos', [])
                if turnos_sp:
                    turnos_db = db.query(Turno).filter(
                        Turno.Turno.in_(turnos_sp),
                        Turno.Id_Estatus == 1
                    ).all()
                    turnos_formatted = [{"id": t.Id_Turno, "nombre": t.Turno} for t in turnos_db]
                    print(f"🕐 Turnos mapeados ({len(turnos_formatted)}): {[t['nombre'] for t in turnos_formatted]}")
                
                # Mapear Sexos (Opcional, si el SP los retorna)
                sexos_db = db.query(Sexo).filter(Sexo.Id_Estatus == 1).all()
                sexos_formatted = [{"id": s.Id_Sexo, "nombre": s.Sexo} for s in sexos_db]
                print(f"⚧ Sexos disponibles: {[s['nombre'] for s in sexos_formatted]}")
                
                # Extraer edades del SP (pueden venir como números, rangos o comparadores)
                edades_sp = valores_unicos.get('edades', [])
                if edades_sp:
                    # Usar el string como ID y nombre (soporta "<=18", "35-40", ">=65", etc.)
                    edades_formatted = [{"id": edad, "nombre": edad} for edad in edades_sp]
                    print(f"🎂 Edades mapeadas ({len(edades_formatted)}): {edades_sp}")
                else:
                    edades_formatted = []
                
                # Crear mapeo de ID_Programa -> [ID_Modalidad] para filtrado dinámico
                programa_modalidades_map = valores_unicos.get('programa_modalidades', {})
                programa_a_modalidades = {}  # {id_programa: [id_modalidad, ...]}
                
                for prog_db in programas_formatted:
                    prog_nombre = prog_db["nombre"]
                    if prog_nombre in programa_modalidades_map:
                        modalidades_del_programa = programa_modalidades_map[prog_nombre]
                        ids_modalidades = [m["id"] for m in modalidades_formatted if m["nombre"] in modalidades_del_programa]
                        programa_a_modalidades[prog_db["id"]] = ids_modalidades
                
                programa_a_modalidades_json = json.dumps(programa_a_modalidades)
                print(f"🔗 Mapeo ID_Programa -> IDs_Modalidad: {programa_a_modalidades_json}")
            else:
                # Si el SP no retorna datos, dejar todo vacío
                print(f"⚠️ El SP no retornó datos para esta UA/Nivel/Periodo")
                print(f"   No se cargarán programas ni modalidades (esperando datos del SP)")
                programas_formatted = []
                modalidades_formatted = []
                boletas_formatted = []
                generaciones_formatted = []
                turnos_formatted = []
                sexos_formatted = []
                edades_formatted = []
                programa_a_modalidades_json = "{}"
                    
        except Exception as e:
            print(f"❌ Error al obtener metadatos del SP: {str(e)}")
            import traceback
            traceback.print_exc()

    # === VERIFICAR RECHAZO PARA CAPTURISTAS ===
    rechazo_info = None
    matricula_rechazada = False
    if es_capturista and id_unidad_academica > 0:
        try:
            # Nota: Validacion no tiene Id_Unidad_Academica en su estructura actual
            # Verificamos por periodo y formato solamente
            ultimo_rechazo = db.query(Validacion).filter(
                Validacion.Id_Periodo == periodo_default_id,
                Validacion.Id_Formato == 3,  # Formato 3 = Egresados
                Validacion.Validado == False
            ).order_by(Validacion.Fecha.desc()).first()
            
            if ultimo_rechazo:
                matricula_rechazada = True
                rechazo_info = {
                    "motivo": ultimo_rechazo.Nota,
                    "rechazado_por": ultimo_rechazo.Usuario,
                    "fecha": ultimo_rechazo.Fecha.strftime("%d/%m/%Y %H:%M") if ultimo_rechazo.Fecha else "N/A",
                    "periodo": periodo_default_literal
                }
                print(f"⚠️ Egresados rechazados por: {rechazo_info['rechazado_por']}")
        except Exception as e:
            print(f"Error al verificar rechazo: {str(e)}")

    # Obtener datos del semáforo para las pestañas de turnos (primeros 3 registros)
    semaforo_estados = db.query(CatSemaforo).filter(CatSemaforo.Id_Semaforo.in_([1, 2, 3])).order_by(CatSemaforo.Id_Semaforo).all()
    semaforo_data = []
    for estado in semaforo_estados:
        # Asegurar que el color tenga el símbolo # al inicio
        color = estado.Color_Semaforo
        if color and not color.startswith('#'):
            color = f"#{color}"
        
        semaforo_data.append({
            'id': estado.Id_Semaforo,
            'descripcion': estado.Descripcion_Semaforo,
            'color': color
        })
    
    print(f"📊 Estados del semáforo cargados: {len(semaforo_data)}")
    for estado in semaforo_data:
        print(f"  - ID {estado['id']}: {estado['descripcion']} ({estado['color']})")

    # Renderizar la plantilla - usar egresados_consulta_limpio.html para todos los roles
    template_name = "egresados_consulta_limpio.html"
    
    print(f"📄 Renderizando template: {template_name}")
    
    return templates.TemplateResponse(template_name, {
        "request": request,
        "nombre_usuario": nombre_completo,
        "nombre_rol": nombre_rol,
        "id_rol": id_rol,
        "periodo_default_id": periodo_default_id,
        "periodo_default_literal": periodo_default_literal,
        "unidad_actual": unidad_actual,
        "programas": programas_formatted,
        "modalidades": modalidades_formatted,
        "boletas": boletas_formatted,
        "generaciones": generaciones_formatted,
        "turnos": turnos_formatted,
        "edades": edades_formatted,
        "sexos": sexos_formatted,
        "es_capturista": es_capturista,
        "es_validador": es_validador,
        "es_rol_director": es_rol_director,
        "es_rol_superior": es_rol_superior,
        "unidades_disponibles": unidades_disponibles,
        "niveles_disponibles": niveles_disponibles,
        "nivel_a_uas_json": nivel_a_uas_json,
        "programa_a_modalidades_json": programa_a_modalidades_json,
        "semaforo_estados": semaforo_data,
        "periodos": periodos,
        "rechazo_info": rechazo_info,
        "matricula_rechazada": matricula_rechazada,
        "acceso_restringido": False
    })


@router.post('/consultar')
async def consultar_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Ejecuta el SP_Consulta_Egresados_Unidad_Academica para obtener datos de egresados
    """
    try:
        data = await request.json()
        
        id_periodo = data.get('id_periodo')
        id_unidad_academica = data.get('id_unidad_academica') or getattr(sess, 'id_unidad_academica', None)
        id_nivel = data.get('id_nivel') or getattr(sess, 'id_nivel', None)  # Recibir id_nivel del frontend o usar sesión
        id_programa = data.get('id_programa')
        id_modalidad = data.get('id_modalidad')
        
        # Obtener información desde cookies
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        host = get_request_host(request)
        
        # Obtener datos de periodo, unidad académica y nivel
        periodo = db.query(Periodo).filter(Periodo.Id_Periodo == id_periodo).first()
        unidad = None
        try:
            if id_unidad_academica is not None:
                unidad = db.query(Unidad_Academica).filter(
                    Unidad_Academica.Id_Unidad_Academica == int(id_unidad_academica)
                ).first()
        except Exception:
            unidad = None

        # Usar el id_nivel enviado desde el frontend o desde la sesión
        nivel = None
        try:
            if id_nivel is not None:
                nivel = db.query(Nivel).filter(Nivel.Id_Nivel == int(id_nivel)).first()
        except Exception:
            nivel = None

        if not all([periodo, unidad, nivel]):
            raise HTTPException(status_code=400, detail="Faltan datos requeridos: periodo, unidad o nivel")
        
        # Para egresados, usar el periodo seleccionado tal cual (sin restar)
        periodo_literal = periodo.Periodo
        unidad_sigla = unidad.Sigla
        nivel_nombre = nivel.Nivel
        
        print(f"\n{'='*60}")
        print(f"📊 EJECUTANDO SP DE CONSULTA DE EGRESADOS")
        print(f"Usuario: {nombre_completo}")
        print(f"Periodo: {periodo_literal} (ID: {id_periodo})")
        print(f"Unidad Académica: {unidad.Nombre} (ID: {id_unidad_academica})")
        print(f"Nivel: {nivel_nombre} (ID: {id_nivel})")
        print(f"{'='*60}")
        
        # Ejecutar el SP
        sp_call = text("""
            EXEC SP_Consulta_Egresados_Unidad_Academica 
                @UUnidad_Academica = :unidad,
                @Pperiodo = :periodo,
                @NNivel = :nivel,
                @UUsuario = :usuario,
                @HHost = :host
        """)
        
        result = db.execute(sp_call, {
            'unidad': unidad_sigla,
            'periodo': periodo_literal,
            'nivel': nivel_nombre,
            'usuario': nombre_completo,
            'host': host
        })
        
        # Obtener todos los resultados
        rows = result.fetchall()
        columns = result.keys()
        
        # Convertir a lista de diccionarios
        egresados_data = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            egresados_data.append(row_dict)
        
        # Filtrar por programa y modalidad si se proporcionan
        if id_programa:
            programa = db.query(Programas).filter(Programas.Id_Programa == id_programa).first()
            if programa:
                egresados_data = [e for e in egresados_data if e.get('Nombre_Programa') == programa.Nombre_Programa]
        
        if id_modalidad:
            modalidad = db.query(Modalidad).filter(Modalidad.Id_Modalidad == id_modalidad).first()
            if modalidad:
                egresados_data = [e for e in egresados_data if e.get('Modalidad') == modalidad.Modalidad]
        
        # Nota: El segundo resultset (nota de rechazo) no está disponible en este contexto
        # ya que CursorResult no tiene método nextset() en SQLAlchemy
        
        print(f"✅ Consulta exitosa: {len(egresados_data)} registros encontrados")
        
        return {
            "success": True,
            "data": egresados_data,
            "count": len(egresados_data)
        }
        
    except Exception as e:
        print(f"❌ Error al consultar egresados: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/guardar')
async def guardar_egresados_temp(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Guarda o actualiza datos de egresados en Temp_Egresados desde la tabla dinámica del frontend
    Los datos se guardarán temporalmente con TODOS los campos en formato TEXTO (no IDs)
    """
    try:
        data = await request.json()
        
        # Obtener datos del request (aceptar tanto 'periodo' como 'id_periodo')
        periodo_id = data.get('periodo') or data.get('id_periodo')
        registros = data.get('registros', [])  # Array con los datos de egresados

        # DEBUG: imprimir payload recibido (recortar si es muy largo)
        try:
            payload_json = json.dumps(data, default=str)
            print(f"[DEBUG REQUEST] /egresados/guardar payload: {payload_json[:2000]}")
        except Exception as e:
            print(f"[DEBUG REQUEST] No se pudo serializar payload: {e}")

        # Soporte para frontend antiguo: payload con id_programa/id_modalidad y registros agregados
        # Formato frontend: registros = [{id_boleta, id_generacion, id_turno, id_sexo, cantidad}, ...]
        # Transformar a formato esperado por este endpoint: registros = [{programa, modalidad, turno, boleta, generacion, edad, hombres, mujeres}, ...]
        if registros and isinstance(registros, list) and isinstance(registros[0], dict) and registros[0].get('id_boleta') is not None:
            id_programa_front = data.get('id_programa') or data.get('programa')
            id_modalidad_front = data.get('id_modalidad') or data.get('modalidad')
            # Agrupar por boleta/generacion/turno
            agrup = {}
            for r in registros:
                try:
                    b = int(r.get('id_boleta') or 0)
                    g = int(r.get('id_generacion') or 0)
                    t = int(r.get('id_turno') or 0)
                    s = int(r.get('id_sexo') or 0)
                    c = int(r.get('cantidad') or 0)
                except Exception:
                    continue

                key = f"{b}_{g}_{t}"
                if key not in agrup:
                    agrup[key] = { 'boleta': b, 'generacion': g, 'turno': t, 'hombres': 0, 'mujeres': 0 }
                if s and c:
                    # Asumir sexo: 1=Hombre, 2=Mujer (si no coincide, se intentará mapear por DB después)
                    if s == 1:
                        agrup[key]['hombres'] += c
                    else:
                        agrup[key]['mujeres'] += c

            # Reconstruir registros en formato esperado
            registros_transformados = []
            for _, v in agrup.items():
                registros_transformados.append({
                    'programa': int(id_programa_front) if id_programa_front else 0,
                    'modalidad': int(id_modalidad_front) if id_modalidad_front else 0,
                    'turno': v['turno'],
                    'boleta': v['boleta'],
                    'generacion': v['generacion'],
                    'edad': '',
                    'hombres': v['hombres'],
                    'mujeres': v['mujeres']
                })

            registros = registros_transformados
            print(f"[DEBUG TRANSFORM] Registros transformados a formato interno: {registros}")

        # Soporte para frontend nuevo: cada fila trae un objeto "turnos" con H/M por turno.
        # Normalizamos a registros planos (uno por turno) para reutilizar el flujo actual.
        if registros and isinstance(registros, list):
            registros_normalizados = []
            formato_turnos_detectado = False

            for reg in registros:
                if not isinstance(reg, dict):
                    continue

                turnos_reg = reg.get('turnos')

                if isinstance(turnos_reg, dict):
                    formato_turnos_detectado = True

                    for turno_id, valores_turno in turnos_reg.items():
                        valores_turno = valores_turno or {}
                        reg_plano = dict(reg)
                        reg_plano['turno'] = turno_id
                        reg_plano['hombres'] = valores_turno.get('hombres', '')
                        reg_plano['mujeres'] = valores_turno.get('mujeres', '')
                        registros_normalizados.append(reg_plano)
                else:
                    registros_normalizados.append(reg)

            if formato_turnos_detectado:
                print(
                    f"[DEBUG NORMALIZE] Formato con turnos detectado: "
                    f"{len(registros)} fila(s) -> {len(registros_normalizados)} registro(s) plano(s)"
                )

            registros = registros_normalizados
        
        # Obtener información del usuario desde cookies
        nombre_usuario = sess.nombre_usuario
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        host = get_request_host(request)
        
        print(f"\n{'='*60}")
        print(f"GUARDANDO EN TEMP_EGRESADOS")
        print(f"Usuario: {nombre_usuario}")
        print(f"Periodo ID: {periodo_id}")
        print(f"Unidad Académica ID: {id_unidad_academica}")
        print(f"Nivel ID: {id_nivel}")
        print(f"Total registros: {len(registros)}")
        print(f"{'='*60}\n")
        
        if not periodo_id or not registros:
            raise HTTPException(status_code=400, detail="Faltan parámetros requeridos (periodo o registros)")
        
        if id_unidad_academica == 0:
            raise HTTPException(status_code=400, detail="No se pudo identificar la unidad académica del usuario")
        
        # Convertir período de ID a formato literal (ej: '2025-2026/1')
        if str(periodo_id).isdigit():
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_id)).first()
            if periodo_obj:
                # IMPORTANTE: El SP usa el periodo ANTERIOR (Id_Periodo - 1)
                # Por lo tanto, debemos guardar en Temp_Egresados con el periodo anterior
                periodo_anterior_id = periodo_obj.Id_Periodo - 1
                periodo_anterior_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_anterior_id).first()
                
                if periodo_anterior_obj:
                    periodo = periodo_anterior_obj.Periodo
                    print(f"🔄 Período convertido: ID actual {periodo_id} → ID anterior {periodo_anterior_id} → '{periodo}' para Temp_Egresados")
                    print(f"   (El SP usa Id_Periodo - 1 internamente)")
                else:
                    raise HTTPException(status_code=400, detail=f"Periodo anterior (ID {periodo_anterior_id}) no encontrado")
            else:
                raise HTTPException(status_code=400, detail=f"Periodo ID {periodo_id} no encontrado")
        else:
            # Si el frontend envía el periodo en formato literal (ej. '2025-2026/1'),
            # debemos convertirlo al periodo ANTERIOR para guardar en Temp_Egresados.
            periodo_literal = str(periodo_id)
            try:
                periodo_obj_literal = db.query(Periodo).filter(Periodo.Periodo == periodo_literal).first()
                if periodo_obj_literal and periodo_obj_literal.Id_Periodo:
                    periodo_anterior_id = periodo_obj_literal.Id_Periodo - 1
                    periodo_anterior_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_anterior_id).first()
                    if periodo_anterior_obj:
                        periodo = periodo_anterior_obj.Periodo
                        print(f"🔄 Período literal convertido: '{periodo_literal}' → periodo anterior '{periodo}' (ID {periodo_anterior_id}) para Temp_Egresados")
                    else:
                        periodo = periodo_literal
                        print(f"⚠️ No se encontró periodo anterior para '{periodo_literal}', usando literal como fallback")
                else:
                    periodo = periodo_literal
                    print(f"⚠️ Periodo literal '{periodo_literal}' no encontrado en Cat_Periodo, usando tal cual")
            except Exception as e:
                periodo = periodo_literal
                print(f"⚠️ Error al convertir periodo literal a anterior: {e}; usando '{periodo_literal}'")
        
        # Obtener Sigla de la Unidad Académica
        unidad_obj = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        
        if not unidad_obj or not unidad_obj.Sigla:
            raise HTTPException(status_code=400, detail="No se pudo obtener la Sigla de la Unidad Académica")
        
        sigla_unidad = unidad_obj.Sigla
        print(f"🏫 Sigla Unidad Académica: {sigla_unidad}")
        
        # Obtener Nivel en formato texto
        nivel_obj = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        nivel_texto = nivel_obj.Nivel if nivel_obj else ""
        
        # Limpiar registros previos de esta UA/Periodo/Nivel
        # Esto evita conflictos de PK y datos obsoletos
        registros_previos = db.query(Temp_Egresados).filter(
            Temp_Egresados.Periodo == periodo,
            Temp_Egresados.Sigla == sigla_unidad,
            Temp_Egresados.Nivel == nivel_texto
        ).delete(synchronize_session=False)
        db.commit()
        print(f"🧹 Limpiados {registros_previos} registros previos de Temp_Egresados")
        print(f"   (Periodo='{periodo}', Sigla='{sigla_unidad}', Nivel='{nivel_texto}')\n")
        
        # LOG: Mostrar todos los registros recibidos
        print(f"📋 REGISTROS RECIBIDOS DEL FRONTEND ({len(registros)} total):")
        for idx, reg in enumerate(registros, 1):
            h = reg.get('hombres', '')
            m = reg.get('mujeres', '')
            edad = reg.get('edad', '?')
            turno_dbg = reg.get('turno', '?')
            print(f"   {idx}. Edad={edad}, Turno={turno_dbg}, H='{h}', M='{m}', Programa={reg.get('programa', '?')}")
        print()
        
        guardados = 0
        errores = []
        
        for idx, registro in enumerate(registros):
            try:
                # Obtener valores de hombres y mujeres (pueden estar vacíos)
                hombres_raw = registro.get('hombres', '')
                mujeres_raw = registro.get('mujeres', '')
                
                # Convertir a int solo si no están vacíos
                hombres = int(hombres_raw) if hombres_raw != '' else 0
                mujeres = int(mujeres_raw) if mujeres_raw != '' else 0
                
                # Validar que al menos uno tenga valor
                if hombres == 0 and mujeres == 0:
                    print(f"⏭️ Saltando registro {idx+1}: sin valores")
                    continue
                
                # Extraer IDs de los filtros con validación
                try:
                    id_programa = int(registro.get('programa') or 0)
                    id_modalidad = int(registro.get('modalidad') or 0)
                    id_turno = int(registro.get('turno') or 0)
                    id_boleta = int(registro.get('boleta') or 0)
                    id_generacion = int(registro.get('generacion') or 0)
                    # EDAD: mantener como string (puede ser '<18', '30-34', '>=40', etc.)
                    edad = str(registro.get('edad') or '')
                except (ValueError, TypeError) as e:
                    print(f"❌ Error convirtiendo IDs en registro {idx+1}: {e}")
                    print(f"   Datos recibidos: {registro}")
                    errores.append(f"Registro {idx+1}: Error en formato de datos")
                    continue

                # Validar que los IDs obligatorios no sean 0. Edad puede quedar vacía.
                if not all([id_programa, id_modalidad, id_turno, id_boleta, id_generacion]):
                    print(f"❌ Registro {idx+1}: Faltan datos obligatorios")
                    print(f"   Programa={id_programa}, Modalidad={id_modalidad}, Turno={id_turno}")
                    print(f"   Boleta={id_boleta}, Generacion={id_generacion}, Edad='{edad}'")
                    errores.append(f"Registro {idx+1}: Datos incompletos")
                    continue
                
                print(f"📝 Procesando registro {idx+1}: Edad={edad}, H={hombres}, M={mujeres}")
                
                # Obtener NOMBRES (no IDs) de todas las entidades
                programa = db.query(Programas).filter(Programas.Id_Programa == id_programa).first()
                if not programa:
                    raise ValueError(f"Programa {id_programa} no encontrado")
                
                rama = db.query(Rama).filter(Rama.Id_Rama == programa.Id_Rama_Programa).first()
                modalidad = db.query(Modalidad).filter(Modalidad.Id_Modalidad == id_modalidad).first()
                boleta = db.query(Boleta).filter(Boleta.Id_Boleta == id_boleta).first()
                generacion = db.query(Generacion).filter(Generacion.Id_Generacion == id_generacion).first()
                turno = db.query(Turno).filter(Turno.Id_Turno == id_turno).first()
                
                # Obtener semáforo actual
                semaforo = db.query(SemaforoUnidadAcademica).filter(
                    SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                    SemaforoUnidadAcademica.Id_Periodo == periodo_id,
                    SemaforoUnidadAcademica.Id_Formato == 3  # Formato 3 = Egresados
                ).first()
                id_semaforo = semaforo.Id_Semaforo if semaforo else 1
                
                # Guardar registro para HOMBRES (si > 0)
                if hombres > 0:
                    temp_egr = Temp_Egresados(
                        Periodo=periodo,
                        Sigla=sigla_unidad,
                        Nombre_Programa=programa.Nombre_Programa,
                        Nombre_Rama=rama.Nombre_Rama if rama else "",
                        Nivel=nivel_texto,
                        Modalidad=modalidad.Modalidad if modalidad else "",
                        Grupo_Edad=str(edad),
                        Boleta=boleta.Boleta if boleta else id_boleta,
                        Generacion=generacion.Generacion if generacion else "",
                        Turno=turno.Turno if turno else "",
                        Sexo='Hombre',
                        Id_Semaforo=id_semaforo,
                        Egresados=hombres
                    )
                    # DEBUG: mostrar payload antes de insertar y opcional pausa
                    try:
                        debug_pause = request.cookies.get("debug_pause", "0") == "1"
                    except Exception:
                        debug_pause = False

                    temp_payload = {
                        'Periodo': periodo,
                        'Sigla': sigla_unidad,
                        'Nombre_Programa': programa.Nombre_Programa,
                        'Nombre_Rama': rama.Nombre_Rama if rama else "",
                        'Nivel': nivel_texto,
                        'Modalidad': modalidad.Modalidad if modalidad else "",
                        'Grupo_Edad': str(edad),
                        'Boleta': boleta.Boleta if boleta else id_boleta,
                        'Generacion': generacion.Generacion if generacion else "",
                        'Turno': turno.Turno if turno else "",
                        'Sexo': 'Hombre',
                        'Id_Semaforo': id_semaforo,
                        'Egresados': hombres
                    }
                    print(f"[DEBUG] A punto de guardar (Hombre) en Temp_Egresados: {temp_payload}")
                    if debug_pause:
                        print("[DEBUG] Pausa activada: esperando 2 segundos antes de guardar...")
                        time.sleep(2)
                    db.merge(temp_egr)
                    guardados += 1
                    print(f"   ➕ HOMBRE: {programa.Nombre_Programa}, Edad={edad}, Valor={hombres}")
                
                # Guardar registro para MUJERES (si > 0)
                if mujeres > 0:
                    temp_egr = Temp_Egresados(
                        Periodo=periodo,
                        Sigla=sigla_unidad,
                        Nombre_Programa=programa.Nombre_Programa,
                        Nombre_Rama=rama.Nombre_Rama if rama else "",
                        Nivel=nivel_texto,
                        Modalidad=modalidad.Modalidad if modalidad else "",
                        Grupo_Edad=str(edad),
                        Boleta=boleta.Boleta if boleta else id_boleta,
                        Generacion=generacion.Generacion if generacion else "",
                        Turno=turno.Turno if turno else "",
                        Sexo='Mujer',
                        Id_Semaforo=id_semaforo,
                        Egresados=mujeres
                    )
                    # DEBUG: mostrar payload antes de insertar y opcional pausa
                    try:
                        debug_pause = request.cookies.get("debug_pause", "0") == "1"
                    except Exception:
                        debug_pause = False

                    temp_payload = {
                        'Periodo': periodo,
                        'Sigla': sigla_unidad,
                        'Nombre_Programa': programa.Nombre_Programa,
                        'Nombre_Rama': rama.Nombre_Rama if rama else "",
                        'Nivel': nivel_texto,
                        'Modalidad': modalidad.Modalidad if modalidad else "",
                        'Grupo_Edad': str(edad),
                        'Boleta': boleta.Boleta if boleta else id_boleta,
                        'Generacion': generacion.Generacion if generacion else "",
                        'Turno': turno.Turno if turno else "",
                        'Sexo': 'Mujer',
                        'Id_Semaforo': id_semaforo,
                        'Egresados': mujeres
                    }
                    print(f"[DEBUG] A punto de guardar (Mujer) en Temp_Egresados: {temp_payload}")
                    if debug_pause:
                        print("[DEBUG] Pausa activada: esperando 2 segundos antes de guardar...")
                        time.sleep(2)
                    db.merge(temp_egr)
                    guardados += 1
                    print(f"   ➕ MUJER: {programa.Nombre_Programa}, Edad={edad}, Valor={mujeres}")
                        
            except Exception as e:
                error_msg = f"Error en registro {idx+1}: {str(e)}"
                print(f"❌ {error_msg}")
                errores.append(error_msg)
                continue
        
        # Confirmar transacción
        db.commit()
        
        # Verificar inmediatamente que se guardaron
        verificacion = db.query(Temp_Egresados).filter(
            Temp_Egresados.Periodo == periodo
        ).count()
        print(f"✅ VERIFICACIÓN: {verificacion} registros en Temp_Egresados con Periodo='{periodo}'")
        
        # Mostrar algunos registros guardados
        if verificacion > 0:
            sample = db.query(Temp_Egresados).filter(
                Temp_Egresados.Periodo == periodo
            ).limit(3).all()
            print(f"📋 Muestra de registros guardados:")
            for s in sample:
                print(f"   - Periodo='{s.Periodo}', Sigla='{s.Sigla}', Programa='{s.Nombre_Programa}', Egresados={s.Egresados}")
        
        mensaje = f"✅ Guardados en Temp_Egresados: {guardados} registros"
        if errores:
            mensaje += f" | Errores: {len(errores)}"
        
        print(f"\n{'='*60}")
        print(mensaje)
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "message": mensaje,
            "guardados": guardados,
            "actualizados": 0,
            "errores": errores if errores else []
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar en Temp_Egresados: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/validar')
async def validar_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Valida los datos de egresados.
    Ejecuta el SP [dbo].[SP_Valida_Egresados] (Formato 3) para avanzar semáforo y registrar en Validacion.
    """
    try:
        data = await request.json()

        periodo_in = data.get('periodo')
        nota_in = (data.get('nota') or '').strip()

        # Sesión
        id_rol = int(sess.id_rol)
        usuario_sp = sess.usuario or 'sistema'  # LOGIN
        unidad_sigla = (sess.sigla_unidad_academica or '').strip()
        nivel_literal = (sess.nombre_nivel or '').strip()
        host_sp = get_request_host(request)

        # Roles permitidos
        if id_rol not in [4, 5, 6, 7, 8, 9]:
            return {"success": False, "message": "Solo roles de validación pueden ejecutar esta acción."}

        # Resolver periodo a literal (si llega como ID)
        if periodo_in is None:
            return {"success": False, "message": "No se recibió el periodo."}

        if str(periodo_in).isdigit():
            per = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_in)).first()
            periodo_literal = per.Periodo if per else str(periodo_in)
        else:
            periodo_literal = str(periodo_in)

        if not unidad_sigla:
            # Fallback: obtener sigla por id_unidad
            try:
                ua = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == int(sess.id_unidad_academica)).first()
                unidad_sigla = ua.Sigla if ua else ''
            except Exception:
                unidad_sigla = ''

        if not unidad_sigla:
            return {"success": False, "message": "No se pudo resolver la Unidad Académica."}

        if not nivel_literal:
            # En SP_Valida_Egresados se compara Cat_Nivel.nivel contra @NNivel
            # Si tu sesión guarda el Id y no el nombre, aquí habría que mapearlo.
            nivel_literal = str(sess.id_nivel)

        nota_sp = nota_in or f"Validado por {sess.nombre_completo}"

        # Para logging: leer semáforo actual si existe
        try:
            periodo_id_db = db.query(Periodo.Id_Periodo).filter(Periodo.Periodo == periodo_literal).scalar()
            sem = db.query(SemaforoUnidadAcademica).filter(
                SemaforoUnidadAcademica.Id_Periodo == periodo_id_db,
                SemaforoUnidadAcademica.Id_Unidad_Academica == int(sess.id_unidad_academica),
                SemaforoUnidadAcademica.Id_Formato == 3,
            ).first()
            sem_actual = sem.Id_Semaforo if sem else None
        except Exception:
            sem_actual = None

        print(f"\n{'='*60}")
        print("✅ VALIDAR EGRESADOS (SP_Valida_Egresados)")
        print(f"Usuario: {usuario_sp} | Rol: {id_rol}")
        print(f"Periodo: {periodo_literal} | UA: {unidad_sigla} | Nivel: {nivel_literal}")
        print(f"Semáforo actual (si aplica): {sem_actual}")
        print(f"Host: {host_sp}")
        print(f"{'='*60}\n")

        sql = text("""
            EXEC [dbo].[SP_Valida_Egresados]
                @PPeriodo = :periodo,
                @UUnidad_Academica = :ua,
                @NNivel = :nivel,
                @UUsuario = :usuario,
                @HHost = :host,
                @semaforo = :semaforo,
                @NNota = :nota
        """)

        db.execute(sql, {
            'periodo': periodo_literal,
            'ua': unidad_sigla,
            'nivel': nivel_literal,
            'usuario': usuario_sp,
            'host': host_sp,
            'semaforo': int(sem_actual) if sem_actual is not None else 0,
            'nota': nota_sp,
        })

        db.commit()

        return {"success": True, "message": "Egresados validados correctamente"}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al validar egresados: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/rechazar')
async def rechazar_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Rechaza los datos de egresados.
    Ejecuta el SP [dbo].[SP_Rechaza_Egresados] (Formato 3) para regresar semáforo y registrar en Validacion.
    """
    try:
        data = await request.json()

        periodo_in = data.get('periodo')
        motivo = (data.get('motivo') or '').strip()

        if not motivo:
            raise HTTPException(status_code=400, detail="Debe proporcionar un motivo de rechazo")

        # Respetar nvarchar(250)
        if len(motivo) > 250:
            motivo = motivo[:250]

        # Sesión
        id_rol = int(sess.id_rol)
        usuario_sp = sess.usuario or 'sistema'
        unidad_sigla = (sess.sigla_unidad_academica or '').strip()
        nivel_literal = (sess.nombre_nivel or '').strip()
        host_sp = get_request_host(request)

        if id_rol not in [4, 5, 6, 7, 8, 9]:
            return {"success": False, "message": "Solo roles de validación pueden ejecutar esta acción."}

        if periodo_in is None:
            return {"success": False, "message": "No se recibió el periodo."}

        if str(periodo_in).isdigit():
            per = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_in)).first()
            periodo_literal = per.Periodo if per else str(periodo_in)
        else:
            periodo_literal = str(periodo_in)

        if not unidad_sigla:
            try:
                ua = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == int(sess.id_unidad_academica)).first()
                unidad_sigla = ua.Sigla if ua else ''
            except Exception:
                unidad_sigla = ''

        if not unidad_sigla:
            return {"success": False, "message": "No se pudo resolver la Unidad Académica."}

        if not nivel_literal:
            nivel_literal = str(sess.id_nivel)

        print(f"\n{'='*60}")
        print("🔴 RECHAZAR EGRESADOS (SP_Rechaza_Egresados)")
        print(f"Usuario: {usuario_sp} | Rol: {id_rol}")
        print(f"Periodo: {periodo_literal} | UA: {unidad_sigla} | Nivel: {nivel_literal}")
        print(f"Host: {host_sp}")
        print(f"Motivo: {motivo}")
        print(f"{'='*60}\n")

        sql = text("""
            EXEC [dbo].[SP_Rechaza_Egresados]
                @PPeriodo = :periodo,
                @UUnidad_Academica = :ua,
                @NNivel = :nivel,
                @UUsuario = :usuario,
                @HHost = :host,
                @NNota = :nota
        """)

        db.execute(sql, {
            'periodo': periodo_literal,
            'ua': unidad_sigla,
            'nivel': nivel_literal,
            'usuario': usuario_sp,
            'host': host_sp,
            'nota': motivo,
        })

        db.commit()

        return {"success": True, "message": "Egresados rechazados. Se notificará al capturista."}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al rechazar egresados: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/guardar_avance")
async def guardar_avance_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para Guardar Avance de Egresados.
    Ejecuta el SP SP_Actualiza_Egresados_Por_Unidad_Academica para actualizar 
    la tabla Egresados con los datos de Temp_Egresados y actualizar el semáforo a estado 2 (En Proceso).
    """
    try:
        # Obtener datos del usuario desde cookies
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        # Obtener unidad académica desde cookies
        unidad_sigla = request.cookies.get("unidad_sigla", "")
        if not unidad_sigla:
            id_unidad_cookie = int(sess.id_unidad_academica)
            if id_unidad_cookie:
                unidad_obj = db.query(Unidad_Academica).filter(
                    Unidad_Academica.Id_Unidad_Academica == id_unidad_cookie
                ).first()
                if unidad_obj and unidad_obj.Sigla:
                    unidad_sigla = unidad_obj.Sigla
        
        # Obtener usuario y host
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        # Obtener período desde el request
        data = await request.json()
        periodo_input = data.get('periodo')
        
        # Convertir a formato literal para buscar en Temp_Egresados
        # IMPORTANTE: Buscamos con el periodo ANTERIOR porque /guardar guardó con Id_Periodo - 1
        if periodo_input:
            if str(periodo_input).isdigit():
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_input)).first()
                if periodo_obj:
                    # Para buscar en Temp_Egresados: usar periodo anterior
                    periodo_anterior_id = periodo_obj.Id_Periodo - 1
                    periodo_anterior_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_anterior_id).first()
                    periodo_busqueda = periodo_anterior_obj.Periodo if periodo_anterior_obj else None
                    
                    # Para pasar al SP: usar periodo ACTUAL (el SP hará la conversión internamente)
                    periodo_sp = periodo_obj.Periodo
                    
                    print(f"🔄 Periodo para buscar en Temp: '{periodo_busqueda}' (ID {periodo_anterior_id})")
                    print(f"🔄 Periodo para pasar al SP: '{periodo_sp}' (ID {periodo_input})")
                else:
                    _, periodo_sp = get_ultimo_periodo(db)
                    periodo_busqueda = periodo_sp
            else:
                periodo_sp = str(periodo_input)
                periodo_busqueda = periodo_sp
        else:
            # Obtener periodo actual y calcular periodo anterior para buscar en Temp_Egresados
            periodo_actual_id, periodo_actual_literal = get_ultimo_periodo(db)
            periodo_sp = periodo_actual_literal
            periodo_busqueda = periodo_sp
            try:
                periodo_anterior_id = int(periodo_actual_id) - 1 if periodo_actual_id else None
                if periodo_anterior_id:
                    periodo_anterior_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_anterior_id).first()
                    if periodo_anterior_obj:
                        periodo_busqueda = periodo_anterior_obj.Periodo
                        print(f"🔄 Período por defecto (anterior) para Temp: '{periodo_busqueda}' (ID {periodo_anterior_id})")
            except Exception:
                # Si algo falla, usar el literal del periodo actual como búsqueda (fallback)
                periodo_busqueda = periodo_sp
        
        # Obtener nivel
        nivel = sess.nombre_nivel
        
        if not all([unidad_sigla, periodo_sp, nivel]):
            return {
                "error": "Faltan parámetros obligatorios",
                "detalles": {
                    "unidad_sigla": unidad_sigla,
                    "periodo": periodo_sp,
                    "nivel": nivel
                }
            }
        
        print(f"\n{'='*60}")
        print(f"GUARDANDO AVANCE DE EGRESADOS")
        print(f"Usuario: {usuario_sp}")
        print(f"Unidad Académica: {unidad_sigla}")
        print(f"Período para SP: {periodo_sp}")
        print(f"Período para buscar: {periodo_busqueda}")
        print(f"Nivel: {nivel}")
        print(f"Host: {host_sp}")
        print(f"{'='*60}")
        
        # Verificar que hay datos en Temp_Egresados antes de actualizar
        print(f"🔍 Buscando registros con Periodo='{periodo_busqueda}', Sigla='{unidad_sigla}', Nivel='{nivel}'")
        temp_count = db.query(Temp_Egresados).filter(
            Temp_Egresados.Periodo == periodo_busqueda,
            Temp_Egresados.Sigla == unidad_sigla,
            Temp_Egresados.Nivel == nivel
        ).count()
        
        print(f"📊 Registros encontrados: {temp_count}")
        
        # Si no hay datos, mostrar diagnóstico
        if temp_count == 0:
            total_registros = db.query(Temp_Egresados).count()
            print(f"⚠️ No se encontraron registros con Periodo='{periodo_busqueda}' para UA='{unidad_sigla}' y Nivel='{nivel}'")
            print(f"⚠️ Total registros en Temp_Egresados: {total_registros}")

            # Mostrar los periodos que SÍ existen
            periodos_existentes = db.query(Temp_Egresados.Periodo).distinct().all()
            print(f"⚠️ Periodos existentes en la tabla:")
            for p in periodos_existentes:
                print(f"   - '{p[0]}'")

            return {
                "warning": "No hay datos en Temp_Egresados para actualizar",
                "registros_temp": 0,
                "periodo_buscado": periodo_busqueda,
                "unidad": unidad_sigla,
                "nivel": nivel,
                "total_registros": total_registros,
                "periodos_existentes": [p[0] for p in periodos_existentes]
            }
        
        print(f"✅ Registros encontrados (Periodo={periodo_busqueda}): {temp_count}")
        
        # Ejecutar el stored procedure con el periodo ACTUAL (el SP hará la conversión)
        sql = text("""
            EXEC [dbo].[SP_Actualiza_Egresados_Por_Unidad_Academica]
                @UUnidad_Academica = :unidad,
                @UUsuario = :usuario,
                @PPeriodo = :periodo,
                @HHost = :host,
                @NNivel = :nivel
        """)
        
        result = db.execute(sql, {
            'unidad': unidad_sigla,
            'usuario': usuario_sp,
            'periodo': periodo_sp,  # Pasar periodo ACTUAL al SP
            'host': host_sp,
            'nivel': nivel
        })
        
        db.commit()
        
        print(f"✅ SP ejecutado exitosamente - Avance guardado")
        
        return {
            "success": True,
            "mensaje": "Avance guardado exitosamente. Los datos han sido actualizados en la tabla Egresados.",
            "registros_procesados": temp_count,
            "semaforo_actualizado": "En Proceso (ID=2)"
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al guardar avance: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error al guardar el avance: {str(e)}"}


@router.post("/finalizar_captura")
async def finalizar_captura_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para Finalizar Captura de Egresados.
    Ejecuta el SP SP_Actualiza_Egresados_Por_Semestre_AU que:
    1. Actualiza el semáforo del semestre específico a estado 3 (Completado)
    2. Llama internamente a SP_Actualiza_Egresados_Por_Unidad_Academica
    3. Devuelve la consulta actualizada de egresados
    """
    try:
        # Obtener datos del usuario desde cookies
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        # Obtener unidad académica desde cookies
        unidad_sigla = request.cookies.get("unidad_sigla", "")
        if not unidad_sigla:
            id_unidad_cookie = int(sess.id_unidad_academica)
            if id_unidad_cookie:
                unidad_obj = db.query(Unidad_Academica).filter(
                    Unidad_Academica.Id_Unidad_Academica == id_unidad_cookie
                ).first()
                if unidad_obj and unidad_obj.Sigla:
                    unidad_sigla = unidad_obj.Sigla
        
        # Obtener usuario y host
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        # Obtener parámetros desde el request
        data = await request.json()
        periodo_input = data.get('periodo')
        programa_id = data.get('programa')
        modalidad_id = data.get('modalidad')
        
        # Convertir período a formato literal
        if periodo_input:
            if str(periodo_input).isdigit():
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_input)).first()
                if periodo_obj:
                    periodo = periodo_obj.Periodo
                else:
                    _, periodo = get_ultimo_periodo(db)
            else:
                periodo = str(periodo_input)
        else:
            _, periodo = get_ultimo_periodo(db)
        
        # Obtener nivel
        nivel = sess.nombre_nivel
        
        # Obtener nombres literales de programa y modalidad
        programa_obj = db.query(Programas).filter(Programas.Id_Programa == int(programa_id)).first()
        programa_nombre = programa_obj.Nombre_Programa if programa_obj else ''
        
        modalidad_obj = db.query(Modalidad).filter(Modalidad.Id_Modalidad == int(modalidad_id)).first()
        modalidad_nombre = modalidad_obj.Modalidad if modalidad_obj else ''
        
        if not all([unidad_sigla, programa_nombre, modalidad_nombre, periodo, nivel]):
            return {
                "error": "Faltan parámetros obligatorios",
                "detalles": {
                    "unidad_sigla": unidad_sigla,
                    "programa": programa_nombre,
                    "modalidad": modalidad_nombre,
                    "periodo": periodo,
                    "nivel": nivel
                }
            }
        
        print(f"\n{'='*60}")
        print(f"FINALIZANDO CAPTURA DE EGRESADOS")
        print(f"Usuario: {usuario_sp}")
        print(f"Unidad Académica: {unidad_sigla}")
        print(f"Programa: {programa_nombre}")
        print(f"Modalidad: {modalidad_nombre}")
        print(f"Período: {periodo}")
        print(f"Nivel: {nivel}")
        print(f"Host: {host_sp}")
        print(f"{'='*60}")
        
        # Determinar periodo de búsqueda en Temp_Egresados (usualmente el periodo anterior)
        periodo_busqueda = periodo
        try:
            # Intentar obtener Id del periodo literal actual y buscar el anterior
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()
            if periodo_obj and periodo_obj.Id_Periodo:
                periodo_anterior_id = int(periodo_obj.Id_Periodo) - 1
                periodo_anterior_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_anterior_id).first()
                if periodo_anterior_obj:
                    periodo_busqueda = periodo_anterior_obj.Periodo
                    print(f"🔄 Periodo para buscar en Temp (anterior): '{periodo_busqueda}' (ID {periodo_anterior_id})")
        except Exception:
            periodo_busqueda = periodo

        # Verificar que hay datos en Temp_Egresados para la UA/nivel y periodo esperados
        temp_count = db.query(Temp_Egresados).filter(
            Temp_Egresados.Periodo == periodo_busqueda,
            Temp_Egresados.Sigla == unidad_sigla,
            Temp_Egresados.Nivel == nivel
        ).count()
        print(f"📊 Registros en Temp_Egresados (Periodo='{periodo_busqueda}', UA='{unidad_sigla}', Nivel='{nivel}'): {temp_count}")
        
        # Ejecutar el stored procedure
        sql = text("""
            EXEC [dbo].[SP_Actualiza_Egresados_Por_Semestre_AU]
                @UUnidad_Academica = :unidad,
                @PPrograma = :programa,
                @MModalidad = :modalidad,
                @UUsuario = :usuario,
                @PPeriodo = :periodo,
                @HHost = :host,
                @NNivel = :nivel
        """)
        
        if temp_count == 0:
            total_registros = db.query(Temp_Egresados).count()
            periodos_existentes = db.query(Temp_Egresados.Periodo).distinct().all()
            print(f"⚠️ No hay registros en Temp_Egresados para Periodo='{periodo_busqueda}', UA='{unidad_sigla}', Nivel='{nivel}'")
            return {
                "warning": "No hay datos en Temp_Egresados para finalizar la captura",
                "periodo_buscado": periodo_busqueda,
                "unidad": unidad_sigla,
                "nivel": nivel,
                "total_registros": total_registros,
                "periodos_existentes": [p[0] for p in periodos_existentes]
            }

        result = db.execute(sql, {
            'unidad': unidad_sigla,
            'programa': programa_nombre,
            'modalidad': modalidad_nombre,
            'usuario': usuario_sp,
            'periodo': periodo,
            'host': host_sp,
            'nivel': nivel
        })
        
        # Obtener todos los resultados (el SP devuelve la consulta actualizada)
        rows_list = []
        try:
            for row in result:
                rows_list.append(dict(row._mapping))
            result.close()
        except Exception as e:
            print(f"⚠️ No se pudieron obtener resultados del SP: {str(e)}")
        
        db.commit()
        
        print(f"✅ SP ejecutado exitosamente - Captura finalizada")
        print(f"📋 Registros devueltos: {len(rows_list)}")
        
        return {
            "success": True,
            "mensaje": f"Captura de {programa_nombre} ({modalidad_nombre}) finalizada exitosamente.",
            "semaforo_actualizado": "Completado (ID=3)",
            "registros_procesados": temp_count,
            "datos_actualizados": rows_list
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al finalizar captura: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error al finalizar la captura: {str(e)}"}


@router.get('/informe')
async def obtener_informe_egresados(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Obtiene el informe de egresados desde el SP para mostrar en la tabla de informe.
    Devuelve los datos reales guardados en la base de datos.
    """
    try:
        # Obtener datos del usuario desde cookies
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel_cookie = sess.id_nivel
        
        if id_nivel_cookie == "None" or id_nivel_cookie is None or id_nivel_cookie == "":
            id_nivel = 0
        else:
            id_nivel = int(id_nivel_cookie)
        
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        print(f"\n{'='*60}")
        print(f"OBTENIENDO INFORME DE EGRESADOS")
        print(f"Usuario: {nombre_completo}")
        print(f"ID Unidad Académica: {id_unidad_academica}")
        print(f"ID Nivel: {id_nivel}")
        print(f"{'='*60}")
        
        # Obtener periodo activo
        periodo_id, periodo_literal = get_ultimo_periodo(db)
        if not periodo_id or not periodo_literal:
            return {"success": False, "error": "No hay un periodo activo configurado"}
        
        # Obtener información de unidad y nivel
        unidad_actual = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        
        if not unidad_actual:
            return {"success": False, "error": "No se pudo identificar la unidad académica"}
        
        nivel = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        nivel_nombre = nivel.Nivel if nivel else ""
        
        # Ejecutar SP para obtener datos
        egresados_data, _ = execute_egresados_sp(
            db=db,
            unidad_sigla=unidad_actual.Sigla,
            periodo_literal=periodo_literal,
            nivel_nombre=nivel_nombre,
            usuario=nombre_completo,
            host=get_request_host(request)
        )
        
        print(f"📊 Datos obtenidos del SP: {len(egresados_data)} registros (antes de filtrar)")
        
        # Filtrar solo registros donde Egresados no sea NULL
        egresados_filtrados = []
        for registro in egresados_data:
            egresados = registro.get('Egresados')
            
            # Incluir solo si Egresados no es NULL
            if egresados is not None:
                egresados_filtrados.append(registro)
        
        print(f"✅ Datos filtrados: {len(egresados_filtrados)} registros (con egresados != NULL)")
        
        return {
            "success": True,
            "datos": egresados_filtrados,
            "total_registros": len(egresados_filtrados)
        }
        
    except Exception as e:
        print(f"❌ Error al obtener informe: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post('/estados_semaforo')
async def obtener_estados_semaforo_por_turnos(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para obtener los estados de semáforo por turno.
    
    Retorna un diccionario con el formato: { "turnoId": estadoId }
    Ejemplo: { "1": 2, "2": 1, "3": 3 } donde 1=Matutino, 2=Vespertino, 3=Mixto
    
    Estados de semáforo:
    - 1: Rojo (Sin datos o incompleto)
    - 2: Amarillo (En proceso)
    - 3: Verde (Completado)
    """
    try:
        data = await request.json()
        periodo_input = data.get('periodo')
        programa_id = data.get('programa')
        modalidad_id = data.get('modalidad')
        
        # Obtener información del usuario
        id_unidad_academica = getattr(sess, 'id_unidad_academica', None)
        id_nivel = getattr(sess, 'id_nivel', None)
        
        if not id_unidad_academica or not id_nivel:
            return {"success": False, "error": "No se pudo identificar la unidad académica o nivel"}
        
        # Convertir período a ID
        if periodo_input:
            if str(periodo_input).isdigit():
                periodo_id = int(periodo_input)
            else:
                periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo_input).first()
                periodo_id = periodo_obj.Id_Periodo if periodo_obj else None
        else:
            periodo_id, _ = get_ultimo_periodo(db)
        
        if not periodo_id:
            return {"success": False, "error": "No se pudo identificar el período"}
        
        # Obtener el Id_Modalidad_Programa para la combinación programa + modalidad
        modalidad_programa_id = None
        if programa_id and modalidad_id:
            prog_mod = db.query(ProgramaModalidad).filter(
                ProgramaModalidad.Id_Programa == int(programa_id),
                ProgramaModalidad.Id_Modalidad == int(modalidad_id)
            ).first()
            if prog_mod:
                modalidad_programa_id = prog_mod.Id_Modalidad_Programa
        
        print(f"\n{'='*60}")
        print(f"OBTENIENDO ESTADOS DE SEMÁFORO POR TURNOS")
        print(f"Período ID: {periodo_id}")
        print(f"Unidad Académica ID: {id_unidad_academica}")
        print(f"Formato: 3 (Egresados)")
        print(f"Programa ID: {programa_id}")
        print(f"Modalidad ID: {modalidad_id}")
        print(f"Modalidad-Programa ID: {modalidad_programa_id}")
        print(f"{'='*60}")
        
        # ========================================================================
        # 🔴 NOTA: Ajustar esta consulta según la estructura real de la BD
        # ========================================================================
        # En la tabla SemaforoSemestreUnidadAcademica:
        # - Id_Semestre podría corresponder al Id_Turno (1=Matutino, 2=Vespertino, 3=Mixto)
        # - O podría necesitarse una consulta diferente según el SP
        #
        # Por ahora, consulto SemaforoSemestreUnidadAcademica asumiendo que Id_Semestre = Id_Turno
        estados_semaforo = {}
        
        if modalidad_programa_id:
            # Consultar estados de semáforo por "semestre" (que podrían ser turnos)
            registros = db.query(SemaforoSemestreUnidadAcademica).filter(
                SemaforoSemestreUnidadAcademica.Id_Periodo == periodo_id,
                SemaforoSemestreUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoSemestreUnidadAcademica.Id_Formato == 3,  # Formato 3 = Egresados
                SemaforoSemestreUnidadAcademica.Id_Modalidad_Programa == modalidad_programa_id
            ).all()
            
            print(f"📊 Registros encontrados en SemaforoSemestreUnidadAcademica: {len(registros)}")
            
            for registro in registros:
                # Asumimos que Id_Semestre corresponde al Id_Turno
                # Ajustar si la lógica es diferente
                turno_id = registro.Id_Semestre
                estado_id = registro.Id_Semaforo
                estados_semaforo[str(turno_id)] = estado_id
                print(f"  🚦 Turno {turno_id}: Estado {estado_id}")
        
        # Si no hay estados registrados, inicializar todos los turnos en rojo (1)
        if not estados_semaforo:
            print("⚠️ No se encontraron estados de semáforo, inicializando todos en rojo (1)")
            # Obtener todos los turnos disponibles
            turnos = db.query(Turno).all()
            for turno in turnos:
                estados_semaforo[str(turno.Id_Turno)] = 1  # Estado 1 = Rojo (sin datos)
        
        print(f"✅ Estados de semáforo a retornar: {estados_semaforo}")
        
        return {
            "success": True,
            "estados_semaforo": estados_semaforo
        }
        
    except Exception as e:
        print(f"❌ Error al obtener estados de semáforo: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get('/resumen-dinamico')
async def resumen_egresados_dinamico_view(
    request: Request, 
    periodo: str,
    nivel: str,
    unidad: str, sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Vista de resumen dinámico de egresados con estructura adaptativa.
    Muestra por Programa → Modalidad → Boletas → Generaciones → Tipo (Regular/Extemporáneo) → Género (H/M/T).
    """
    # Obtener datos del usuario logueado
    id_rol = int(sess.id_rol)
    nombre_rol = sess.nombre_rol
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Validar que el usuario tenga rol superior (4-9)
    roles_permitidos = [1, 4, 5, 6, 7, 8, 9]
    if id_rol not in roles_permitidos:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Acceso denegado: Su rol ({nombre_rol}) no tiene permisos para acceder a esta funcionalidad.",
            "redirect_url": "/mod_principal/"
        })

    print(f"\n{'='*60}")
    print(f"RESUMEN DINÁMICO DE EGRESADOS")
    print(f"Periodo: {periodo}, Nivel: {nivel}, Unidad: {unidad}")
    print(f"Usuario: {nombre_completo} ({nombre_rol})")
    print(f"{'='*60}")

    try:
        # ------------------------------------------------------------
        # Resolver Id_Periodo (para validación/rechazo desde la vista)
        # ------------------------------------------------------------
        from backend.database.models.CatPeriodo import CatPeriodo

        periodo_obj = db.query(CatPeriodo).filter(CatPeriodo.Periodo == periodo).first()
        periodo_id = int(periodo_obj.Id_Periodo) if periodo_obj else None

        # Obtener datos del SP de egresados
        host = get_request_host(request)
        usuario_login = sess.usuario
        
        egresados_data, nota_rechazo = execute_egresados_sp(
            db=db,
            unidad_sigla=unidad,
            periodo_literal=periodo,
            nivel_nombre=nivel,
            usuario=nombre_completo,
            host=host
        )

        # ------------------------------------------------------------
        # Estado de validación/rechazo (roles 4-9)
        # ------------------------------------------------------------
        puede_validar = False
        usuario_ya_valido = False
        usuario_ya_rechazo = False
        esperando_por_rol = None

        try:
            if id_rol in [4, 5, 6, 7, 8, 9] and periodo_id is not None:
                semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
                    SemaforoUnidadAcademica.Id_Periodo == periodo_id,
                    SemaforoUnidadAcademica.Id_Unidad_Academica == int(sess.id_unidad_academica),
                    SemaforoUnidadAcademica.Id_Formato == 3  # Formato 3 = Egresados
                ).first()

                estado_semaforo = semaforo_unidad.Id_Semaforo if semaforo_unidad else None

                # Regla de jerarquía real (alineada a los SPs de Validar/Rechazar):
                # SP_Valida_Egresados y SP_Rechaza_Egresados validan que:
                #   sua.Id_Semaforo == (Id_Rol del usuario) - 1
                # Esto permite pasos distintos para 6,7,8,9 en vez de agruparlos.
                semaforo_esperado = id_rol - 1

                if estado_semaforo is not None:
                    if estado_semaforo == semaforo_esperado:
                        puede_validar = True
                        usuario_ya_valido = False
                        usuario_ya_rechazo = False
                    elif estado_semaforo > semaforo_esperado:
                        usuario_ya_valido = True
                    else:
                        # Aún no toca este nivel
                        puede_validar = False
                        try:
                            # El primer rol por defecto debe ser Capturista (Id_Rol 2)
                            # Si el semáforo está en 1 o 2, está esperando al Capturista
                            if estado_semaforo in [1, 2]:
                                esperando_por_rol = "Capturista"
                            else:
                                rol_esperado_id = int(estado_semaforo) + 1
                                rol_obj = db.query(CatRoles).filter(CatRoles.Id_Rol == rol_esperado_id).first()
                                esperando_por_rol = rol_obj.Rol if rol_obj else "Capturista"
                        except Exception:
                            esperando_por_rol = "Capturista"
                else:
                    # Si no hay semáforo configurado, el primer paso siempre es Capturista
                    esperando_por_rol = "Capturista"

                # Si ya rechazó, ocultar botones (salvo que el semáforo esté justo en el nivel esperado)
                try:
                    id_usuario_actual = int(sess.id_usuario)
                    rechazo_usuario = db.query(Validacion).filter(
                        Validacion.Id_Periodo == periodo_id,
                        Validacion.Id_Usuario == id_usuario_actual,
                        Validacion.Id_Formato == 3,
                        Validacion.Validado == 0
                    ).first()
                    if rechazo_usuario:
                        if not puede_validar:
                            usuario_ya_rechazo = True
                except Exception:
                    # Si algo falla aquí, no bloqueamos por seguridad de UI
                    pass
        except Exception:
            # Si algo falla, solo no mostramos estado (UI seguirá normal)
            pass

        if not egresados_data:
            return templates.TemplateResponse("egresados_resumen_dinamico.html", {
                "request": request,
                "nombre_usuario": nombre_completo,
                "nombre_rol": nombre_rol,
                "id_rol": id_rol,
                "periodo": periodo,
                "periodo_id": periodo_id,
                "nivel": nivel,
                "unidad": unidad,
                "datos_resumen": [],
                "generaciones": [],
                "boletas_columnas": [],
                "filas_pivot": [],
            "modalidades_columnas": [],
            "filas_boleta_modalidad": [],
            "programa_counts": {},
            "turnos_columnas": [],
            "edades_columnas": [],
            "filas_edad_turno": [],
            "programa_counts_edad": {},
                "total_general": {"boletas": {}, "total_h": 0, "total_m": 0, "total_t": 0},
                "puede_validar": puede_validar,
                "usuario_ya_valido": usuario_ya_valido,
                "usuario_ya_rechazo": usuario_ya_rechazo,
                "esperando_por_rol": esperando_por_rol,
                "error_message": "No hay datos disponibles para los filtros seleccionados"
            })

        print(f"📊 Total de registros del SP: {len(egresados_data)}")

        def _get_row_value(row: dict, *keys, default=None):
            """Obtiene un valor del row soportando variantes de nombre de columna."""
            for key in keys:
                if key in row and row[key] is not None and str(row[key]).strip() != "":
                    return row[key]

            normalized = {
                ''.join(ch for ch in str(k).lower() if ch.isalnum()): v
                for k, v in row.items()
            }
            for key in keys:
                norm_key = ''.join(ch for ch in str(key).lower() if ch.isalnum())
                value = normalized.get(norm_key)
                if value is not None and str(value).strip() != "":
                    return value

            return default

        # === PROCESAR DATOS PARA EL RESUMEN DINÁMICO ===
        from collections import defaultdict
        
        # 1. Extraer generaciones únicas y ordenarlas
        generaciones_set = set()
        for row in egresados_data:
            gen = _get_row_value(row, 'Generacion', 'Generación')
            if gen:
                generaciones_set.add(str(gen))
        
        generaciones = sorted(list(generaciones_set), reverse=True)  # Más reciente primero
        print(f"📅 Generaciones detectadas: {generaciones}")
        
        # Determinar cuál es la generación regular (la más reciente)
        generacion_regular = generaciones[0] if generaciones else None
        print(f"📌 Generación REGULAR: {generacion_regular} (más reciente)")
        
        # 2. Estructura para agrupar datos por Programa → Modalidad → Boleta
        # estructura[programa][modalidad][boleta] = {...datos por generación...}
        estructura: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        
        # 3. Procesar cada registro del SP
        for row in egresados_data:
            programa = str(_get_row_value(row, 'Nombre_Programa', 'Programa', default='Sin Programa')).strip() or 'Sin Programa'
            modalidad = str(_get_row_value(row, 'Modalidad', default='Sin Modalidad')).strip() or 'Sin Modalidad'
            generacion = str(_get_row_value(row, 'Generacion', 'Generación', default='Sin generación')).strip() or 'Sin generación'
            boleta_raw = _get_row_value(row, 'Boleta', default='S/B')
            boleta = str(boleta_raw).strip() if boleta_raw is not None else 'S/B'
            if not boleta:
                boleta = 'S/B'
            
            # Mapear Sexo: "HOMBRE" -> "H", "MUJER" -> "M"
            sexo_raw = str(_get_row_value(row, 'Sexo', default='M')).upper()
            if 'HOMBRE' in sexo_raw or sexo_raw == 'H':
                sexo = 'H'
            elif 'MUJER' in sexo_raw or sexo_raw == 'M':
                sexo = 'M'
            else:
                sexo = 'M'  # Default
            
            egresados_raw = _get_row_value(row, 'Egresados', default=0)
            try:
                egresados = int(float(egresados_raw)) if egresados_raw not in (None, '') else 0
            except (TypeError, ValueError):
                egresados = 0
            
            # Determinar si es Regular o Extemporáneo desde el campo Generacion
            # Si viene "Generación Regular" o contiene "Regular" -> regular
            # Si viene "Generación Extemporanea" o años antiguos -> extemporaneo
            generacion_lower = generacion.lower()
            if 'regular' in generacion_lower:
                tipo_key = 'regular'
            elif 'extemporanea' in generacion_lower or 'extemporaneo' in generacion_lower:
                tipo_key = 'extemporaneo'
            else:
                # Fallback: generación más reciente es regular
                tipo_key = 'regular' if generacion == generacion_regular else 'extemporaneo'
            
            #print(f"  📝 {programa} | {modalidad} | Bol:{boleta} | Gen:{generacion} ({tipo_key}) | {sexo}: {egresados}")
            
            # Inicializar estructura jerárquica de forma explícita
            programa_data = estructura.setdefault(programa, {})
            modalidad_data = programa_data.setdefault(modalidad, {})
            if boleta not in modalidad_data:
                modalidad_data[boleta] = {
                    'generaciones': {},
                    'total_h': 0,
                    'total_m': 0,
                    'total_t': 0
                }

            boleta_data = modalidad_data[boleta]
            generaciones_data = boleta_data['generaciones']
            if generacion not in generaciones_data:
                generaciones_data[generacion] = {
                    'regular': {'H': 0, 'M': 0, 'T': 0},
                    'extemporaneo': {'H': 0, 'M': 0, 'T': 0}
                }

            # Acumular egresados por generación y tipo
            generaciones_data[generacion][tipo_key][sexo] += egresados
            generaciones_data[generacion][tipo_key]['T'] += egresados

            # Acumular totales generales de esta boleta
            boleta_data['total_' + sexo.lower()] += egresados
            boleta_data['total_t'] += egresados
        
        # 4. Convertir estructura a lista para el template
        # Cada fila = Programa + Modalidad + Boleta literal
        datos_resumen = []
        for programa in sorted(estructura.keys()):
            for modalidad in sorted(estructura[programa].keys()):
                # Obtener todas las boletas de esta modalidad y ordenarlas numéricamente
                boletas_dict = estructura[programa][modalidad]
                boletas_ordenadas = sorted(
                    boletas_dict.keys(),
                    key=lambda x: (0, int(str(x))) if str(x).isdigit() else (1, str(x))
                )
                
                for boleta in boletas_ordenadas:
                    datos_boleta = boletas_dict[boleta]
                    
                    # Preparar datos de generaciones en el orden correcto
                    gen_data = []
                    for gen in generaciones:
                        gen_values = datos_boleta['generaciones'].get(gen, {
                            'regular': {'H': 0, 'M': 0, 'T': 0},
                            'extemporaneo': {'H': 0, 'M': 0, 'T': 0}
                        })
                        gen_data.append({
                            'generacion': gen,
                            'regular': gen_values['regular'],
                            'extemporaneo': gen_values['extemporaneo']
                        })
                    
                    datos_resumen.append({
                        'programa': programa,
                        'modalidad': modalidad,
                        'boleta': boleta,  # Boleta literal (1, 2, 3, etc.)
                        'generaciones': gen_data,
                        'total_h': datos_boleta['total_h'],
                        'total_m': datos_boleta['total_m'],
                        'total_t': datos_boleta['total_t']
                    })

        # 5. Construir estructura pivotada: filas por Programa+Modalidad y boletas como columnas
        boletas_global = set()
        for programa in estructura:
            for modalidad in estructura[programa]:
                boletas_global.update(estructura[programa][modalidad].keys())

        boletas_columnas = sorted(
            list(boletas_global),
            key=lambda x: (0, int(str(x))) if str(x).isdigit() else (1, str(x))
        )

        filas_pivot = []
        total_general = {
            'boletas': {
                b: {
                    'regular': {'H': 0, 'M': 0, 'T': 0},
                    'extemporaneo': {'H': 0, 'M': 0, 'T': 0}
                } for b in boletas_columnas
            },
            'total_h': 0,
            'total_m': 0,
            'total_t': 0
        }

        for programa in sorted(estructura.keys()):
            for modalidad in sorted(estructura[programa].keys()):
                boletas_data = {}
                row_total_h = 0
                row_total_m = 0
                row_total_t = 0

                for boleta in boletas_columnas:
                    if boleta in estructura[programa][modalidad]:
                        datos_boleta = estructura[programa][modalidad][boleta]

                        regular_h = regular_m = regular_t = 0
                        ext_h = ext_m = ext_t = 0

                        for _, gen_values in datos_boleta['generaciones'].items():
                            regular_h += gen_values['regular']['H']
                            regular_m += gen_values['regular']['M']
                            regular_t += gen_values['regular']['T']

                            ext_h += gen_values['extemporaneo']['H']
                            ext_m += gen_values['extemporaneo']['M']
                            ext_t += gen_values['extemporaneo']['T']

                        boletas_data[boleta] = {
                            'regular': {'H': regular_h, 'M': regular_m, 'T': regular_t},
                            'extemporaneo': {'H': ext_h, 'M': ext_m, 'T': ext_t}
                        }

                        row_total_h += regular_h + ext_h
                        row_total_m += regular_m + ext_m
                        row_total_t += regular_t + ext_t

                        total_general['boletas'][boleta]['regular']['H'] += regular_h
                        total_general['boletas'][boleta]['regular']['M'] += regular_m
                        total_general['boletas'][boleta]['regular']['T'] += regular_t
                        total_general['boletas'][boleta]['extemporaneo']['H'] += ext_h
                        total_general['boletas'][boleta]['extemporaneo']['M'] += ext_m
                        total_general['boletas'][boleta]['extemporaneo']['T'] += ext_t
                    else:
                        boletas_data[boleta] = {
                            'regular': {'H': 0, 'M': 0, 'T': 0},
                            'extemporaneo': {'H': 0, 'M': 0, 'T': 0}
                        }

                total_general['total_h'] += row_total_h
                total_general['total_m'] += row_total_m
                total_general['total_t'] += row_total_t

                filas_pivot.append({
                    'programa': programa,
                    'modalidad': modalidad,
                    'boletas': boletas_data,
                    'total_h': row_total_h,
                    'total_m': row_total_m,
                    'total_t': row_total_t
                })
        
        print(f"✅ Resumen procesado: {len(datos_resumen)} filas (Programa+Modalidad+Boleta)")
        print(f"📊 Generaciones: {len(generaciones)}")
        print(f"📊 Boletas en columnas: {len(boletas_columnas)}")
        print(f"📊 Filas pivotadas (Programa+Modalidad): {len(filas_pivot)}")
        
        
        # ============================================================
        # 6. TABLAS DINÁMICAS (NUEVO FORMATO)
        #    Tabla 1: Programa | Generación | Boleta | Modalidad(H/M/T...) | Total(H/M/T)
        #    Tabla 2: Programa | Generación | Edad   | Turno(H/M/T...)     | Total(H/M/T)
        # ============================================================
        from collections import defaultdict

        def _is_nullish(v) -> bool:
            if v is None:
                return True
            s = str(v).strip()
            return (s == "" or s.upper() in ("NULL", "NONE", "N/A", "NA"))

        modalidades_set = set()
        boletas_set = set()
        turnos_set = set()
        edades_set = set()

        # data_boleta[programa][tipo][boleta][modalidad] = {'H':..,'M':..,'T':..}
        data_boleta = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'H': 0, 'M': 0, 'T': 0}))))

        # data_edad[programa][tipo][edad][turno] = {'H':..,'M':..,'T':..}
        data_edad = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'H': 0, 'M': 0, 'T': 0}))))

        for row in egresados_data:
            programa = str(_get_row_value(row, 'Nombre_Programa', 'Programa', default='Sin Programa')).strip() or 'Sin Programa'
            modalidad = str(_get_row_value(row, 'Modalidad', default='Sin Modalidad')).strip() or 'Sin Modalidad'
            generacion = str(_get_row_value(row, 'Generacion', 'Generación', default='')).strip()

            # Boleta (filtrar nulls)
            boleta_raw = _get_row_value(row, 'Boleta', default=None)
            if _is_nullish(boleta_raw):
                continue
            boleta = str(boleta_raw).strip()

            # Sexo
            sexo_raw = str(_get_row_value(row, 'Sexo', default='M')).upper()
            if 'HOMBRE' in sexo_raw or sexo_raw == 'H':
                sexo = 'H'
            elif 'MUJER' in sexo_raw or sexo_raw == 'M':
                sexo = 'M'
            else:
                sexo = 'M'

            # Egresados (filtrar 0 para no "inflar" tablas con combinaciones vacías)
            eg_raw = _get_row_value(row, 'Egresados', default=0)
            try:
                eg = int(float(eg_raw)) if eg_raw not in (None, '') else 0
            except (TypeError, ValueError):
                eg = 0
            if eg <= 0:
                continue

            # Tipo de generación (regular/extemporaneo)
            generacion_lower = generacion.lower()
            if 'extemporanea' in generacion_lower or 'extemporaneo' in generacion_lower:
                tipo = 'extemporaneo'
            elif 'regular' in generacion_lower:
                tipo = 'regular'
            else:
                # fallback con la generación más reciente detectada
                tipo = 'regular' if generacion and generacion == generacion_regular else 'extemporaneo'

            modalidades_set.add(modalidad)
            boletas_set.add(boleta)

            # Tabla 1 acumula por boleta + modalidad
            celda = data_boleta[programa][tipo][boleta][modalidad]
            celda[sexo] += eg
            celda['T'] += eg

            # Tabla 2 acumula por edad + turno (si existen)
            # Intentar primero Grupo_Edad, luego Edad como fallback
            edad_raw = _get_row_value(row, 'Grupo_Edad', 'Edad', default=None)
            turno_raw = _get_row_value(row, 'Turno', default=None)
            if not _is_nullish(edad_raw) and not _is_nullish(turno_raw):
                edad = str(edad_raw).strip()
                turno = str(turno_raw).strip()
                edades_set.add(edad)
                turnos_set.add(turno)

                celda2 = data_edad[programa][tipo][edad][turno]
                celda2[sexo] += eg
                celda2['T'] += eg

        # Columnas ordenadas
        modalidades_columnas = sorted(list(modalidades_set))

        boletas_columnas_row = sorted(
            list(boletas_set),
            key=lambda x: (0, int(str(x))) if str(x).isdigit() else (1, str(x))
        )

        def _sort_mixed_numbers(values):
            def key(v):
                s = str(v).strip()
                return (0, int(s)) if s.isdigit() else (1, s)
            return sorted(values, key=key)

        turnos_columnas = sorted(list(turnos_set))
        edades_columnas = _sort_mixed_numbers(list(edades_set))

        # Inicializar totales generales SIEMPRE (incluso si no hay datos)
        totales_tabla1 = {'modalidades': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0}
        totales_tabla2 = {'turnos': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0}
        
        # Inicializar estructuras para modalidades y turnos
        for mod in modalidades_columnas:
            totales_tabla1['modalidades'][mod] = {'H': 0, 'M': 0, 'T': 0}
        for turno in turnos_columnas:
            totales_tabla2['turnos'][turno] = {'H': 0, 'M': 0, 'T': 0}
        
        # Inicializar subtotales por generación
        subtotales_generacion_tabla1 = {
            'regular': {'modalidades': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0},
            'extemporaneo': {'modalidades': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0}
        }
        subtotales_generacion_tabla2 = {
            'regular': {'turnos': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0},
            'extemporaneo': {'turnos': {}, 'total_h': 0, 'total_m': 0, 'total_t': 0}
        }
        
        # Inicializar modalidades y turnos para cada tipo de generación
        for tipo in ['regular', 'extemporaneo']:
            for mod in modalidades_columnas:
                subtotales_generacion_tabla1[tipo]['modalidades'][mod] = {'H': 0, 'M': 0, 'T': 0}
            for turno in turnos_columnas:
                subtotales_generacion_tabla2[tipo]['turnos'][turno] = {'H': 0, 'M': 0, 'T': 0}

        # Construir filas para Tabla 1
        filas_boleta_modalidad = []
        programa_counts = {}
        

        for programa in sorted(data_boleta.keys()):
            reg_boletas = _sort_mixed_numbers(list(data_boleta[programa].get('regular', {}).keys()))
            ext_boletas = _sort_mixed_numbers(list(data_boleta[programa].get('extemporaneo', {}).keys()))

            programa_counts[programa] = {
                'regular': len(reg_boletas),
                'extemporaneo': len(ext_boletas),
                'total': len(reg_boletas) + len(ext_boletas)
            }

            for tipo, boletas_lista in (('regular', reg_boletas), ('extemporaneo', ext_boletas)):
                for boleta in boletas_lista:
                    modalidades_data = {}
                    total_h = total_m = total_t = 0

                    for mod in modalidades_columnas:
                        v = data_boleta[programa][tipo][boleta].get(mod, {'H': 0, 'M': 0, 'T': 0})
                        modalidades_data[mod] = v
                        total_h += v.get('H', 0)
                        total_m += v.get('M', 0)
                        total_t += v.get('T', 0)
                        
                        # Acumular en totales globales
                        totales_tabla1['modalidades'][mod]['H'] += v.get('H', 0)
                        totales_tabla1['modalidades'][mod]['M'] += v.get('M', 0)
                        totales_tabla1['modalidades'][mod]['T'] += v.get('T', 0)
                        
                        # Acumular en subtotales por generación
                        subtotales_generacion_tabla1[tipo]['modalidades'][mod]['H'] += v.get('H', 0)
                        subtotales_generacion_tabla1[tipo]['modalidades'][mod]['M'] += v.get('M', 0)
                        subtotales_generacion_tabla1[tipo]['modalidades'][mod]['T'] += v.get('T', 0)

                    totales_tabla1['total_h'] += total_h
                    totales_tabla1['total_m'] += total_m
                    totales_tabla1['total_t'] += total_t
                    
                    # Acumular en subtotales por generación
                    subtotales_generacion_tabla1[tipo]['total_h'] += total_h
                    subtotales_generacion_tabla1[tipo]['total_m'] += total_m
                    subtotales_generacion_tabla1[tipo]['total_t'] += total_t

                    filas_boleta_modalidad.append({
                        'programa': programa,
                        'tipo': tipo,
                        'boleta': boleta,
                        'modalidades': modalidades_data,
                        'total_h': total_h,
                        'total_m': total_m,
                        'total_t': total_t
                    })

        # Construir filas para Tabla 2
        filas_edad_turno = []
        programa_counts_edad = {}

        for programa in sorted(data_edad.keys()):
            reg_edades = _sort_mixed_numbers(list(data_edad[programa].get('regular', {}).keys()))
            ext_edades = _sort_mixed_numbers(list(data_edad[programa].get('extemporaneo', {}).keys()))

            programa_counts_edad[programa] = {
                'regular': len(reg_edades),
                'extemporaneo': len(ext_edades),
                'total': len(reg_edades) + len(ext_edades)
            }

            for tipo, edades_lista in (('regular', reg_edades), ('extemporaneo', ext_edades)):
                for edad in edades_lista:
                    turnos_data = {}
                    total_h = total_m = total_t = 0

                    for turno in turnos_columnas:
                        v = data_edad[programa][tipo][edad].get(turno, {'H': 0, 'M': 0, 'T': 0})
                        turnos_data[turno] = v
                        total_h += v.get('H', 0)
                        total_m += v.get('M', 0)
                        total_t += v.get('T', 0)
                        
                        # Acumular en totales globales
                        totales_tabla2['turnos'][turno]['H'] += v.get('H', 0)
                        totales_tabla2['turnos'][turno]['M'] += v.get('M', 0)
                        totales_tabla2['turnos'][turno]['T'] += v.get('T', 0)
                        
                        # Acumular en subtotales por generación
                        subtotales_generacion_tabla2[tipo]['turnos'][turno]['H'] += v.get('H', 0)
                        subtotales_generacion_tabla2[tipo]['turnos'][turno]['M'] += v.get('M', 0)
                        subtotales_generacion_tabla2[tipo]['turnos'][turno]['T'] += v.get('T', 0)

                    totales_tabla2['total_h'] += total_h
                    totales_tabla2['total_m'] += total_m
                    totales_tabla2['total_t'] += total_t
                    
                    # Acumular en subtotales por generación
                    subtotales_generacion_tabla2[tipo]['total_h'] += total_h
                    subtotales_generacion_tabla2[tipo]['total_m'] += total_m
                    subtotales_generacion_tabla2[tipo]['total_t'] += total_t

                    filas_edad_turno.append({
                        'programa': programa,
                        'tipo': tipo,
                        'edad': edad,
                        'turnos': turnos_data,
                        'total_h': total_h,
                        'total_m': total_m,
                        'total_t': total_t
                    })

        return templates.TemplateResponse("egresados_resumen_dinamico.html", {
            "request": request,
            "nombre_usuario": nombre_completo,
            "nombre_rol": nombre_rol,
            "id_rol": id_rol,
            "periodo": periodo,
            "periodo_id": periodo_id,
            "nivel": nivel,
            "unidad": unidad,
            "datos_resumen": datos_resumen,
            "generaciones": generaciones,
            "boletas_columnas": boletas_columnas,
            "filas_pivot": filas_pivot,
            "total_general": total_general,
            "puede_validar": puede_validar,
            "usuario_ya_valido": usuario_ya_valido,
            "usuario_ya_rechazo": usuario_ya_rechazo,
            "esperando_por_rol": esperando_por_rol,
            "modalidades_columnas": modalidades_columnas,
            "filas_boleta_modalidad": filas_boleta_modalidad,
            "programa_counts": programa_counts,
            "turnos_columnas": turnos_columnas,
            "edades_columnas": edades_columnas,
            "filas_edad_turno": filas_edad_turno,
            "programa_counts_edad": programa_counts_edad,
            "totales_tabla1": totales_tabla1,
            "totales_tabla2": totales_tabla2,
            "subtotales_generacion_tabla1": subtotales_generacion_tabla1,
            "subtotales_generacion_tabla2": subtotales_generacion_tabla2,
            "error_message": None
        })
        
    except Exception as e:
        print(f"❌ Error en resumen dinámico: {str(e)}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("egresados_resumen_dinamico.html", {
            "request": request,
            "nombre_usuario": nombre_completo,
            "nombre_rol": nombre_rol,
            "id_rol": id_rol,
            "periodo": periodo,
            "periodo_id": None,
            "nivel": nivel,
            "unidad": unidad,
            "datos_resumen": [],
            "generaciones": [],
            "boletas_columnas": [],
            "filas_pivot": [],
            "total_general": {"boletas": {}, "total_h": 0, "total_m": 0, "total_t": 0},
            "puede_validar": False,
            "usuario_ya_valido": False,
            "usuario_ya_rechazo": False,
            "esperando_por_rol": None,
            "error_message": f"Error al procesar datos: {str(e)}"
        })

