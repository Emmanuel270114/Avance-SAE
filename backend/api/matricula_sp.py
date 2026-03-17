from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
from typing import List, Dict, Any
from fastapi import HTTPException
from datetime import datetime

from backend.core.templates import templates
from backend.core.auth import get_current_session
from backend.database.connection import get_db
from backend.database.models.Matricula import Matricula
from backend.database.models.CatPeriodo import CatPeriodo as Periodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica as Unidad_Academica
from backend.database.models.CatNivel import CatNivel as Nivel
from backend.database.models.CatSemestre import CatSemestre as Semestre
from backend.database.models.CatProgramas import CatProgramas as Programas
from backend.database.models.CatModalidad import CatModalidad as Modalidad
from backend.database.models.CatTurno import CatTurno as Turno
from backend.database.models.CatGrupoEdad import CatGrupoEdad as Grupo_Edad
from backend.database.models.CatTipoIngreso import TipoIngreso as Tipo_Ingreso
from backend.database.models.CatRama import CatRama as Rama
from backend.database.models.CatSemaforo import CatSemaforo
from backend.database.models.SemaforoUnidadAcademica import SemaforoUnidadAcademica
from backend.database.models.SemaforoSemestreUnidadAcademica import SemaforoSemestreUnidadAcademica
from backend.database.models.ProgramaModalidad import ProgramaModalidad
from backend.database.models.Validacion import Validacion
from backend.services.matricula_service import (
    execute_matricula_sp_with_context,
    get_matricula_metadata_from_sp,
    execute_sp_actualiza_matricula_por_unidad_academica,
    execute_sp_actualiza_matricula_por_semestre_au,
    get_estado_semaforo_desde_sp,
    execute_sp_finaliza_captura_matricula,
    execute_sp_valida_matricula,
    execute_sp_rechaza_matricula,
    extract_unique_values_from_sp,
)
from backend.utils.request import get_request_host
from backend.database.models.Temp_Matricula import Temp_Matricula
from backend.database.models.CatRoles import CatRoles
from backend.services.periodo_service import get_periodo_activo, get_ultimo_periodo

router = APIRouter()


@router.get('/consulta')
async def captura_matricula_sp_view(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint principal para la visualización/captura de matrícula usando EXCLUSIVAMENTE Stored Procedures.
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
    es_rol_superior = (id_rol in [4, 5, 6, 7, 8, 9])  # Roles 4-9: pueden ver múltiples UAs con selector
    modo_vista = "captura" if es_capturista else "validacion"

    print(f"\n{'='*60}")
    print(f"CARGANDO VISTA DE MATRÍCULA - TODO DESDE SP")
    print(f"Usuario: {nombre_completo}")
    print(f"Rol: {nombre_rol} (ID: {id_rol})")
    print(f"Modo de vista: {modo_vista.upper()}")
    print(f"Es rol superior (4-9): {es_rol_superior}")
    print(f"ID Unidad Académica: {id_unidad_academica}")
    print(f"ID Nivel: {id_nivel}")
    print(f"{'='*60}")

    # Redirigir roles superiores (4-9) directamente a la vista de resumen selector
    # para que su flujo sea: Matrícula -> Selección de filtros -> Resumen dinámico
    # Nota: Si en algún momento quieres que 4-5 sigan usando la vista
    # de captura con semáforo, cambia la lista a [6, 7, 8, 9].
    if id_rol in [4, 5, 6, 7, 8, 9]:
        return RedirectResponse(url="/matricula/resumen-seleccion", status_code=302)

    # === VERIFICAR ACCESO BASADO EN SEMÁFORO ===
    # Solo roles 4-5 necesitan verificar semáforo de su UA
    # Roles 6-9 NO verifican semáforo porque pueden consultar cualquier UA
    if id_rol in [4, 5]:
        print(f"\n🔐 Verificando acceso para rol {id_rol} - Requiere semáforo >= 3")
        
        # Obtener periodo por defecto (activo o último)
        periodo_activo_tuple = get_periodo_activo(db)
        if periodo_activo_tuple:
            periodo_default_id, periodo_default_literal = periodo_activo_tuple
        else:
            periodo_ultimo_tuple = get_ultimo_periodo(db)
            if periodo_ultimo_tuple:
                periodo_default_id, periodo_default_literal = periodo_ultimo_tuple
            else:
                periodo_default_id = None
                periodo_default_literal = None
        
        print(f"   Periodo para verificación: {periodo_default_literal} (ID: {periodo_default_id})")
        
        # Consultar el estado del semáforo para esta unidad académica
        semaforo = db.query(SemaforoUnidadAcademica).filter(
            SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
            SemaforoUnidadAcademica.Id_Periodo == periodo_default_id,
            SemaforoUnidadAcademica.Id_Formato == 1,  # 1 = Formato de Matrícula
            SemaforoUnidadAcademica.Id_Nivel == id_nivel
        ).first()

        # **OBTENER EL NOMBRE DEL SIGUIENTE ROL BASADO EN EL ESTADO DEL SEMÁFORO**
        # El semáforo indica qué rol validó por última vez
        # Mapeo: Estado del semáforo -> Siguiente rol que debe validar
        semaforo_a_siguiente_rol = {
            3: 4,  # Semáforo 3 (Capturista validó) -> siguiente: CEGET
            4: 5,  # Semáforo 4 (CEGET validó) -> siguiente: Títular
            5: 6,  # Semáforo 5 (Títular validó) -> siguiente: Analista
            6: 7,  # Semáforo 6 (Analista validó) -> siguiente: Jefe de Departamento
            7: 8,  # Semáforo 7 (Jefe Depto validó) -> siguiente: Jefe de División
            8: 9,  # Semáforo 8 (Jefe División validó) -> siguiente: Director
        }
        
        if not semaforo:
            print(f"⚠️ No se encontró semáforo para UA={id_unidad_academica}, Periodo={periodo_default_id}")
            return templates.TemplateResponse("matricula_consulta.html", {
                "request": request,
                "acceso_restringido": True,
                "mensaje_restriccion": "La información aún no está disponible. La unidad académica debe iniciar la captura de matrícula.",
                "nombre_usuario": nombre_completo,
                "nombre_rol": "Capturista",
                "estado_actual": None,
                # Variables requeridas por el template
                "grupos_edad": [],
                "tipos_ingreso": [],
                "semestres": [],
                "semestres_map_json": "{}",
                "periodo_default_literal": periodo_default_literal if 'periodo_default_literal' in locals() else "",
                "periodo_default_id": periodo_default_id,
                "es_capturista": False,
                "es_validador": True,
                "es_rol_superior": False,
                "unidades_disponibles": [],
                "niveles_disponibles": [],
                "nivel_a_uas_json": "{}",
                "modo_vista": "validacion",
                "id_rol": id_rol,
                "semaforo_estados": [],
                "turnos": [],
                "programas": [],
                "modalidades": [],
                "periodos": [],
                "unidades_academicas": [],
                "unidad_actual": None,
                "rechazo_info": None,
                "matricula_rechazada": False,
                "usuario_ya_valido": False,
                "usuario_ya_rechazo": False
            })
        
        # **DETERMINAR EL SIGUIENTE ROL QUE DEBE VALIDAR SEGÚN EL SEMÁFORO**
        siguiente_rol_id = semaforo_a_siguiente_rol.get(semaforo.Id_Semaforo, None)
        nombre_siguiente_rol = "Capturista"  # Valor por defecto

        if siguiente_rol_id:
            siguiente_rol = db.query(CatRoles).filter(CatRoles.Id_Rol == siguiente_rol_id).first()
            if siguiente_rol:
                nombre_siguiente_rol = siguiente_rol.Rol
                print(f"📋 Siguiente rol que debe validar (semáforo={semaforo.Id_Semaforo}): {nombre_siguiente_rol} (ID: {siguiente_rol_id})")
        
        # Permitir el acceso si el semaforo es igual a (id_rol - 1) o (id_rol = 3) o (>= id_rol)
        if semaforo.Id_Semaforo < 3 or semaforo.Id_Semaforo < (id_rol - 1):
            print(f"🚫 ACCESO DENEGADO - Semáforo actual: {semaforo.Id_Semaforo} (requiere >= 3)")
            
            # Obtener descripción del semáforo actual
            semaforo_actual = db.query(CatSemaforo).filter(
                CatSemaforo.Id_Semaforo == semaforo.Id_Semaforo
            ).first()
            
            descripcion_estado = semaforo_actual.Descripcion_Semaforo if semaforo_actual else f"Estado {semaforo.Id_Semaforo}"
            
            return templates.TemplateResponse("matricula_consulta.html", {
                "request": request,
                "acceso_restringido": True,
                "mensaje_restriccion": f"La información aún no está disponible para validación. Esperando que {nombre_siguiente_rol} valide primero.",
                "nombre_usuario": nombre_completo,
                "nombre_rol": nombre_siguiente_rol,
                "estado_actual": descripcion_estado,
                # Variables requeridas por el template
                "grupos_edad": [],
                "tipos_ingreso": [],
                "semestres": [],
                "semestres_map_json": "{}",
                "periodo_default_literal": periodo_default_literal,
                "periodo_default_id": periodo_default_id,
                "es_capturista": False,
                "es_validador": True,
                "es_rol_superior": False,
                "unidades_disponibles": [],
                "niveles_disponibles": [],
                "nivel_a_uas_json": "{}",
                "modo_vista": "validacion",
                "id_rol": id_rol,
                "semaforo_estados": [],
                "turnos": [],
                "programas": [],
                "modalidades": [],
                "periodos": [],
                "unidades_academicas": [],
                "unidad_actual": None,
                "rechazo_info": None,
                "matricula_rechazada": False,
                "usuario_ya_valido": False,
                "usuario_ya_rechazo": False
            })
        
        print(f"✅ ACCESO PERMITIDO - Semáforo en estado {semaforo.Id_Semaforo} (>= 3, Validado)")
    
    # Configurar listas de UAs y Niveles según el rol
    unidades_disponibles = []
    niveles_disponibles = []
    nivel_a_uas_json = "{}"
    
    if id_rol in [4, 5]:
        # Roles 4-5: Solo pueden ver SU UA y Nivel (pre-seleccionados y bloqueados)
        print(f"\n🔒 ROL 4-5 - Configurando filtros restringidos a su UA/Nivel")
        
        # Obtener la UA del usuario
        if id_unidad_academica > 0:
            ua_usuario = db.query(Unidad_Academica).filter(
                Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
            ).first()
            
            if ua_usuario:
                unidades_disponibles = [{
                    'Id_Unidad_Academica': ua_usuario.Id_Unidad_Academica,
                    'Nombre': ua_usuario.Nombre,
                    'Sigla': ua_usuario.Sigla
                }]
                print(f"   ✅ UA asignada: {ua_usuario.Nombre}")
        
        # Obtener el Nivel del usuario
        if id_nivel > 0:
            nivel_usuario = db.query(Nivel).filter(
                Nivel.Id_Nivel == id_nivel
            ).first()
            
            if nivel_usuario:
                niveles_disponibles = [{
                    'Id_Nivel': nivel_usuario.Id_Nivel,
                    'Nivel': nivel_usuario.Nivel
                }]
                print(f"   ✅ Nivel asignado: {nivel_usuario.Nivel}")
        
        # Crear mapeo simple para su UA/Nivel
        if id_nivel > 0 and id_unidad_academica > 0:
            nivel_a_uas = {id_nivel: [id_unidad_academica]}
            nivel_a_uas_json = json.dumps(nivel_a_uas, ensure_ascii=False)
    
    elif id_rol in [6, 7, 8, 9]:
        # Roles 6-9: Pueden ver TODAS las UAs y Niveles
        print(f"\n🔓 ROL 6-9 - Obteniendo todas las UAs y niveles")
        todas_unidades = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Estatus == 1  # Solo activas
        ).order_by(Unidad_Academica.Nombre).all()
        
        todos_niveles = db.query(Nivel).filter(
            Nivel.Id_Estatus == 1  # Solo activos
        ).order_by(Nivel.Id_Nivel).all()
        
        print(f"   ✅ {len(todas_unidades)} UAs disponibles")
        print(f"   ✅ {len(todos_niveles)} niveles disponibles")
        
        # Formatear para el template
        unidades_disponibles = [
            {'Id_Unidad_Academica': ua.Id_Unidad_Academica, 'Nombre': ua.Nombre, 'Sigla': ua.Sigla}
            for ua in todas_unidades
        ]
        niveles_disponibles = [
            {'Id_Nivel': n.Id_Nivel, 'Nivel': n.Nivel}
            for n in todos_niveles
        ]
        
        # Obtener relaciones UA-Nivel desde SemaforoUnidadAcademica
        # Para saber qué UAs tienen matrícula en cada nivel
        relaciones_ua_nivel = db.query(
            SemaforoUnidadAcademica.Id_Unidad_Academica,
            SemaforoUnidadAcademica.Id_Nivel
        ).filter(
            SemaforoUnidadAcademica.Id_Formato == 1  # Solo matrícula
        ).distinct().all()
        
        # Crear mapa: nivel -> [lista de IDs de UAs]
        nivel_a_uas = {}
        
        for rel in relaciones_ua_nivel:
            id_ua = rel.Id_Unidad_Academica
            id_nivel_rel = rel.Id_Nivel
            
            if id_nivel_rel not in nivel_a_uas:
                nivel_a_uas[id_nivel_rel] = []
            if id_ua not in nivel_a_uas[id_nivel_rel]:
                nivel_a_uas[id_nivel_rel].append(id_ua)
        
        print(f"   📋 Relaciones UA-Nivel desde Semaforo: {len(relaciones_ua_nivel)}")
        for id_nivel_map, lista_uas in nivel_a_uas.items():
            nivel_nombre = next((n.Nivel for n in todos_niveles if n.Id_Nivel == id_nivel_map), f"Nivel {id_nivel_map}")
            print(f"      - {nivel_nombre}: {len(lista_uas)} UAs")
        
        # Convertir a JSON para el template
        nivel_a_uas_json = json.dumps(nivel_a_uas, ensure_ascii=False)
    
    # Obtener periodo dinámico desde la base de datos (priorizar activo)
    periodo_default_id, periodo_default_literal = get_periodo_activo(db) or get_ultimo_periodo(db)
    if not periodo_default_id or not periodo_default_literal:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "No hay periodos configurados en el sistema.",
            "redirect_url": "/mod_principal/"
        })
    
    # Obtener SOLO período y unidad desde la base de datos (mínimo necesario)
    periodos = db.query(Periodo).all()
    unidades_academicas = db.query(Unidad_Academica).filter(
        Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
    ).all()
    
    unidad_actual = unidades_academicas[0] if unidades_academicas else None

    # Obtener datos del semáforo para las pestañas (primeros 3 registros)
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

    # Construir mapeo Programa -> Modalidades para filtros dependientes
    programa_a_modalidades: Dict[int, List[int]] = {}
    try:
        relaciones_pm = db.query(ProgramaModalidad).filter(ProgramaModalidad.Id_Estatus == 1).all()
        for rel in relaciones_pm:
            if rel.Id_Programa not in programa_a_modalidades:
                programa_a_modalidades[rel.Id_Programa] = []
            if rel.Id_Modalidad not in programa_a_modalidades[rel.Id_Programa]:
                programa_a_modalidades[rel.Id_Programa].append(rel.Id_Modalidad)
    except Exception as e:
        print(f"⚠️ Error construyendo mapeo Programa->Modalidad: {e}")
    programa_a_modalidades_json = json.dumps(programa_a_modalidades)

    # VERIFICAR SI ES ROL SUPERIOR (6-9): mostrar panel de filtros sin ejecutar SP aún
    if es_rol_superior:
        print(f"\n⏳ ROL SUPERIOR detectado - NO se ejecuta SP inicialmente")
        print(f"   Se mostrará panel de selección de UA y Nivel")
        
        return templates.TemplateResponse("matricula_consulta.html", {
            "request": request,
            "nombre_usuario": nombre_completo,
            "nombre_rol": nombre_rol,
            "id_unidad_academica": id_unidad_academica,
            "id_nivel": id_nivel,
            "id_rol": id_rol,
            "es_capturista": False,
            "es_validador": True,
            "es_rol_superior": True,  # Bandera clave
            "modo_vista": "validacion",
            "periodos": [{'Id_Periodo': p.Id_Periodo, 'Periodo': p.Periodo, 'Id_Estatus': p.Id_Estatus} for p in periodos],
            "unidades_academicas": [],
            "periodo_default_id": periodo_default_id,
            "periodo_default_literal": periodo_default_literal,
            "unidad_actual": unidad_actual,
            # Listas de opciones para el panel de filtros
            "unidades_disponibles": unidades_disponibles,
            "niveles_disponibles": niveles_disponibles,
            "nivel_a_uas_json": nivel_a_uas_json,  # Mapeo para filtrado
            # Datos vacíos hasta que seleccionen
            "programas": [],
            "modalidades": [],
            "semestres": [],
            "semestres_map_json": "{}",
            "turnos": [],
            "grupos_edad": [],
            "tipos_ingreso": [],
            "semaforo_estados": semaforo_data,
            "rechazo_info": None,
            "matricula_rechazada": False,
            "usuario_ya_valido": False,
            "usuario_ya_rechazo": False,
            "programa_a_modalidades_json": programa_a_modalidades_json,
        })

    # ROLES 3, 4, 5: Ejecutar SP con contexto fijo del usuario
    print(f"\n▶ EJECUTANDO SP para roles 3-5 con contexto fijo del usuario")
    
    # Obtener usuario y host para el SP
    usuario_sp = nombre_completo or 'sistema'
    host_sp = get_request_host(request)

    # Obtener TODOS los metadatos desde el SP (con usuario y host)
    # El SP también devuelve la nota de rechazo si existe
    rows_sp, metadata_sp, debug_msg_sp, nota_rechazo_sp = execute_matricula_sp_with_context(
        db=db,
        id_unidad_academica=id_unidad_academica,
        id_nivel=id_nivel,
        periodo_input=periodo_default_literal,
        default_periodo=periodo_default_literal,
        usuario=usuario_sp,
        host=host_sp
    )

    # Usar metadata del SP
    metadata = extract_unique_values_from_sp(rows_sp)

    # Verificar si hubo error
    if 'error' in metadata and metadata['error']:
        print(f"⚠️ Error obteniendo metadatos: {metadata['error']}")

    # Preparar datos para el template
    grupos_edad_labels = metadata.get('grupos_edad', [])
    tipos_ingreso_labels = metadata.get('tipos_ingreso', [])
    programas_labels = metadata.get('programas', [])
    modalidades_labels = metadata.get('modalidades', [])
    semestres_labels = metadata.get('semestres', [])
    turnos_labels = metadata.get('turnos', [])

    # Mapear nombres a objetos de catálogo para obtener IDs
    # Grupos de Edad - SOLO los que devuelve el SP
    grupos_edad_db = db.query(Grupo_Edad).all()
    grupos_edad_map = {str(g.Grupo_Edad): g for g in grupos_edad_db}
    grupos_edad_formatted = []
    for label in grupos_edad_labels:
        if label in grupos_edad_map:
            g = grupos_edad_map[label]
            grupos_edad_formatted.append({
                'Id_Grupo_Edad': g.Id_Grupo_Edad,
                'Grupo_Edad': g.Grupo_Edad
            })
    print(f"📊 DEBUG: Pasando {len(grupos_edad_formatted)} grupos de edad al frontend (solo del SP)")
    
    # Tipos de Ingreso - SOLO los que devuelve el SP
    tipos_ingreso_db = db.query(Tipo_Ingreso).all()
    tipos_ingreso_map = {str(t.Tipo_de_Ingreso): t for t in tipos_ingreso_db}
    tipos_ingreso_formatted = []
    for label in tipos_ingreso_labels:
        if label in tipos_ingreso_map:
            t = tipos_ingreso_map[label]
            tipos_ingreso_formatted.append({
                'Id_Tipo_Ingreso': t.Id_Tipo_Ingreso,
                'Tipo_de_Ingreso': t.Tipo_de_Ingreso
            })
    print(f"📊 DEBUG: Pasando {len(tipos_ingreso_formatted)} tipos de ingreso al frontend (solo del SP)")
    
    # Programas
    programas_db = db.query(Programas).filter(Programas.Id_Nivel == id_nivel).all()
    programas_map = {str(p.Nombre_Programa): p for p in programas_db}
    programas_formatted = []
    for label in programas_labels:
        if label in programas_map:
            p = programas_map[label]
            programas_formatted.append({
                'Id_Programa': p.Id_Programa,
                'Nombre_Programa': p.Nombre_Programa,
                'Id_Semestre': p.Id_Semestre
            })
    
    # Modalidades
    modalidades_db = db.query(Modalidad).all()
    modalidades_map = {str(m.Modalidad): m for m in modalidades_db}
    modalidades_formatted = []
    for label in modalidades_labels:
        if label in modalidades_map:
            m = modalidades_map[label]
            modalidades_formatted.append({'Id_Modalidad': m.Id_Modalidad, 'Modalidad': m.Modalidad})
    
    # Semestres
    semestres_db = db.query(Semestre).all()
    semestres_map_db = {str(s.Semestre): s for s in semestres_db}
    semestres_formatted = []
    for label in semestres_labels:
        if label in semestres_map_db:
            s = semestres_map_db[label]
            semestres_formatted.append({'Id_Semestre': s.Id_Semestre, 'Semestre': s.Semestre})
    
    # Turnos - SOLO los que devuelve el SP
    turnos_db = db.query(Turno).all()
    turnos_map = {str(t.Turno): t for t in turnos_db}
    turnos_formatted = []
    for label in turnos_labels:
        if label in turnos_map:
            t = turnos_map[label]
            turnos_formatted.append({
                'Id_Turno': t.Id_Turno,
                'Turno': t.Turno
            })
    print(f"📊 DEBUG: Pasando {len(turnos_formatted)} turnos al frontend (solo del SP)")

    # Construir un mapping simple para semestres
    semestres_map_json_dict = {s['Id_Semestre']: s['Semestre'] for s in semestres_formatted}
    semestres_map_json = json.dumps(semestres_map_json_dict, ensure_ascii=False)

    # Construir mapeo Programa -> Modalidades para filtros dependientes
    # (también disponible para roles 3-5, reutilizando la misma estructura que roles superiores)
    programa_a_modalidades: Dict[int, List[int]] = {}
    try:
        relaciones_pm = db.query(ProgramaModalidad).filter(ProgramaModalidad.Id_Estatus == 1).all()
        for rel in relaciones_pm:
            if rel.Id_Programa not in programa_a_modalidades:
                programa_a_modalidades[rel.Id_Programa] = []
            if rel.Id_Modalidad not in programa_a_modalidades[rel.Id_Programa]:
                programa_a_modalidades[rel.Id_Programa].append(rel.Id_Modalidad)
    except Exception as e:
        print(f"⚠️ Error construyendo mapeo Programa->Modalidad (roles 3-5): {e}")
    programa_a_modalidades_json = json.dumps(programa_a_modalidades)

    print(f"\n=== METADATOS ENVIADOS AL FRONTEND ===")
    print(f"Grupos de Edad: {len(grupos_edad_formatted)} -> {[g['Grupo_Edad'] for g in grupos_edad_formatted]}")
    print(f"Tipos de Ingreso: {len(tipos_ingreso_formatted)} -> {[t['Tipo_de_Ingreso'] for t in tipos_ingreso_formatted]}")
    print(f"Programas: {len(programas_formatted)} -> {[p['Nombre_Programa'] for p in programas_formatted]}")
    print(f"Modalidades: {len(modalidades_formatted)}")
    print(f"Semestres: {len(semestres_formatted)}")
    print(f"Turnos: {len(turnos_formatted)}")
    
    # DEBUG: Verificar si llegó la nota del SP
    print(f"\n🔍 DEBUG NOTA DE RECHAZO:")
    print(f"   nota_rechazo_sp = {nota_rechazo_sp}")
    print(f"   es_capturista = {es_capturista}")
    print(f"   tipo nota_rechazo_sp = {type(nota_rechazo_sp)}")
    
    # VERIFICAR SI LA MATRÍCULA ESTÁ RECHAZADA (solo para capturistas)
    rechazo_info = None
    if es_capturista:
        print(f"\n🔍 Usuario es CAPTURISTA - Verificando rechazo...")
        
        # Buscar el último rechazo en la base de datos, restringido a la UA actual
        # Si el SP trae la nota (scoped por UA+Periodo), se usará esa; este filtro es fallback seguro
        from backend.database.models.Usuario import Usuario
        ultimo_rechazo = (
            db.query(Validacion)
            .join(Usuario, Usuario.Id_Usuario == Validacion.Id_Usuario)
            .filter(
                Validacion.Id_Periodo == periodo_default_id,
                Validacion.Id_Formato == 1,  # Formato de matrícula
                Validacion.Validado == 0,    # 0 = Rechazo
                Usuario.Id_Unidad_Academica == id_unidad_academica
            )
            .order_by(Validacion.Fecha.desc())
            .first()
        )
        
        if ultimo_rechazo:
            print(f"✅ RECHAZO ENCONTRADO en tabla Validacion")
            
            # Obtener información del usuario que rechazó
            usuario_rechazo = db.query(Usuario).filter(
                Usuario.Id_Usuario == ultimo_rechazo.Id_Usuario
            ).first()
            
            nombre_rechazo = "Validador"
            if usuario_rechazo:
                nombre_rechazo = f"{usuario_rechazo.Nombre} {usuario_rechazo.Paterno} {usuario_rechazo.Materno}".strip()
            
            # Prioridad: usar nota del SP, si no está, usar la nota de la tabla Validacion
            motivo_rechazo = nota_rechazo_sp if nota_rechazo_sp else (ultimo_rechazo.Nota or "Sin especificar motivo")
            
            rechazo_info = {
                'motivo': motivo_rechazo,
                'rechazado_por': nombre_rechazo,
                'fecha': ultimo_rechazo.Fecha.strftime("%d/%m/%Y %H:%M") if ultimo_rechazo.Fecha else "",
                'periodo': periodo_default_literal,
                'unidad': unidad_actual.Nombre if unidad_actual else ""
            }
            
            print(f"📋 Información de rechazo COMPLETA:")
            print(f"   Motivo (de {'SP' if nota_rechazo_sp else 'Validacion'}): {motivo_rechazo[:100] if motivo_rechazo else 'N/A'}...")
            print(f"   Rechazado por: {rechazo_info['rechazado_por']}")
            print(f"   Fecha: {rechazo_info['fecha']}")
        else:
            print(f"✅ NO hay rechazo registrado en tabla Validacion para esta UA")
            
            # Si el SP trajo nota pero no hay registro en Validacion, mostrar advertencia
            if nota_rechazo_sp:
                print(f"⚠️  ANOMALÍA: SP retornó nota pero no hay registro en Validacion:")
                print(f"   Nota del SP: {nota_rechazo_sp[:100]}...")
    else:
        print(f"✅ Usuario NO es capturista - No se verifica rechazo")

# VERIFICAR SI EL USUARIO ACTUAL YA VALIDÓ/RECHAZÓ (para roles de validación)
    usuario_ya_valido = False
    usuario_ya_rechazo = False
    
    if es_validador:
        print(f"\n🔍 Verificando si el usuario (ID: {request.cookies.get('id_usuario')}) ya validó/rechazó...")
        print(f"   Rol del usuario: {id_rol}")
        
        # Obtener el estado del semáforo general de la unidad académica
        semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
            SemaforoUnidadAcademica.Id_Periodo == periodo_default_id,
            SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
            SemaforoUnidadAcademica.Id_Formato == 1  # Formato de matrícula
        ).first()
        
        if semaforo_unidad:
            estado_semaforo = semaforo_unidad.Id_Semaforo
            print(f"   Estado del semáforo: {estado_semaforo}")
            
            # LÓGICA: El usuario puede validar si el semáforo está en (id_rol - 1)
            # Ejemplos:
            # - Rol 4 (CEGET) puede validar si semáforo = 3 (Capturista validó)
            # - Rol 5 (Titular) puede validar si semáforo = 4 (CEGET validó)
            # - Rol 6 (Analista) puede validar si semáforo = 5 (Titular validó)
            
            semaforo_esperado = id_rol - 1
            print(f"   Semáforo esperado para que rol {id_rol} valide: {semaforo_esperado}")
            
            if estado_semaforo == semaforo_esperado:
                # El semáforo está en el nivel correcto, el usuario PUEDE validar
                print(f"✅ Semáforo en nivel correcto ({estado_semaforo}) - Usuario puede validar")
                usuario_ya_valido = False
                usuario_ya_rechazo = False
            elif estado_semaforo >= id_rol:
                # El semáforo ya pasó el nivel del usuario, significa que YA validó
                print(f"🔒 Semáforo ya en nivel {estado_semaforo} (>= {id_rol}) - Usuario ya validó en este nivel")
                usuario_ya_valido = True
            elif estado_semaforo < semaforo_esperado:
                # El semáforo está en un nivel anterior, el usuario NO puede validar aún
                print(f"⏳ Semáforo en nivel {estado_semaforo} (< {semaforo_esperado}) - Usuario debe esperar")
                usuario_ya_valido = False
                usuario_ya_rechazo = False
        else:
            print(f"⚠️ No se encontró semáforo para esta UA/Periodo")
            usuario_ya_valido = False
            usuario_ya_rechazo = False
        
        # Verificar si el usuario rechazó (esto sí necesita verificarse en la tabla Validacion)
        id_usuario_actual = int(sess.id_usuario)
        validacion_rechazo = db.query(Validacion).filter(
            Validacion.Id_Periodo == periodo_default_id,
            Validacion.Id_Usuario == id_usuario_actual,
            Validacion.Id_Formato == 1,
            Validacion.Validado == 0  # Solo rechazos
        ).first()
        
        # Solo bloquear por rechazo si el semáforo NO está en el nivel esperado para validar
        if validacion_rechazo:
            if not (semaforo_unidad and estado_semaforo == (id_rol - 1)):
                usuario_ya_rechazo = True
                print(f"❌ Usuario YA RECHAZÓ esta matrícula (Fecha: {validacion_rechazo.Fecha})")
            else:
                # Semáforo permite validar de nuevo; no bloqueamos por rechazos previos
                print(f"ℹ️ Existe rechazo previo, pero semáforo={estado_semaforo} permite validar nuevamente.")

    # DEBUG FINAL: Verificar qué se va a pasar al template
    print(f"\n📤 DATOS A ENVIAR AL TEMPLATE:")
    print(f"   rechazo_info = {rechazo_info}")
    print(f"   es_capturista = {es_capturista}")
    print(f"   usuario_ya_valido = {usuario_ya_valido}")
    print(f"   usuario_ya_rechazo = {usuario_ya_rechazo}")

    # Bandera para indicar si la matrícula fue rechazada:
    # - Capturista: cuando hay rechazo_info
    # - Validadores: cuando el usuario actual registró rechazo o existe rechazo en la UA/Periodo
    matricula_rechazada = False
    if es_capturista:
        matricula_rechazada = rechazo_info is not None
    else:
        # Si el usuario ya rechazó, entonces la matrícula está rechazada para su vista
        if usuario_ya_rechazo:
            matricula_rechazada = True
        else:
            # Checar si existe cualquier rechazo activo en la UA/Periodo para el formato
            from backend.database.models.Usuario import Usuario
            any_rechazo = (
                db.query(Validacion)
                .join(Usuario, Usuario.Id_Usuario == Validacion.Id_Usuario)
                .filter(
                    Validacion.Id_Periodo == periodo_default_id,
                    Validacion.Id_Formato == 1,
                    Validacion.Validado == 0,
                    Usuario.Id_Unidad_Academica == id_unidad_academica,
                )
                .first()
            )
            matricula_rechazada = any_rechazo is not None
    print(f"   matricula_rechazada = {matricula_rechazada}")

    return templates.TemplateResponse("matricula_consulta.html", {
        "request": request,
        "nombre_usuario": nombre_completo,
        "nombre_rol": nombre_rol,
        "id_unidad_academica": id_unidad_academica,
        "id_nivel": id_nivel,
        "id_rol": id_rol,
        "es_capturista": es_capturista,
        "es_validador": es_validador,
        "es_rol_superior": es_rol_superior,  # Usar la variable calculada (True para roles 4-9)
        "modo_vista": modo_vista,
        "periodos": periodos,
        "unidades_academicas": unidades_academicas,
        "periodo_default_id": periodo_default_id,
        "periodo_default_literal": periodo_default_literal,
        "unidad_actual": unidad_actual,
        "programas": programas_formatted,
        "modalidades": modalidades_formatted,
        "semestres": semestres_formatted,
        "semestres_map_json": semestres_map_json,
        "turnos": turnos_formatted,
        "grupos_edad": grupos_edad_formatted,
        "tipos_ingreso": tipos_ingreso_formatted,
        "semaforo_estados": semaforo_data,
        "rechazo_info": rechazo_info,  # Información del rechazo (None si no está rechazada)
        "matricula_rechazada": matricula_rechazada,  # Bandera para validación masiva
        "usuario_ya_valido": usuario_ya_valido,  # True si el usuario ya validó
        "usuario_ya_rechazo": usuario_ya_rechazo,  # True si el usuario ya rechazó
        # Filas iniciales del SP para evitar una segunda ejecución en la primera carga
        "rows_sp_iniciales": rows_sp,
        # Variables para roles superiores (4-9)
        "unidades_disponibles": unidades_disponibles,
        "niveles_disponibles": niveles_disponibles,
        "nivel_a_uas_json": nivel_a_uas_json,  # Mapeo de Nivel -> UAs
        "programa_a_modalidades_json": programa_a_modalidades_json,
    })

# Endpoint para obtener datos existentes usando SP
@router.post("/obtener_datos_existentes_sp")
async def obtener_datos_existentes_sp(
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener datos existentes usando SP.
    Retorna SOLO las filas del SP sin procesamiento adicional.
    El frontend se encarga de construir la tabla con estos datos.
    """
    try:
        data = await request.json()
        print(f"\n=== DEBUG SP - Parámetros recibidos ===")
        print(f"Datos JSON: {data}")

        # Obtener parámetros del JSON
        periodo_input = data.get('periodo')
        
        # Si periodo es un ID numérico, convertirlo al literal
        if periodo_input:
            # Convertir a string para verificar si es numérico
            periodo_str = str(periodo_input)
            if periodo_str.isdigit():
                periodo_id = int(periodo_str)
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_id).first()
                if periodo_obj:
                    periodo = periodo_obj.Periodo
                    print(f"✓ Periodo convertido de ID {periodo_id} a literal: {periodo}")
                else:
                    # Intentar obtener el periodo activo dinámicamente
                    _, periodo_fallback = get_periodo_activo(db) or get_ultimo_periodo(db)
                    periodo = periodo_fallback if periodo_fallback else None
                    if not periodo:
                        return {"error": "No se encontró el periodo solicitado y no hay periodos configurados en el sistema."}
                    print(f"⚠️ Periodo ID {periodo_id} no encontrado, usando último: {periodo}")
            else:
                # Ya es literal
                periodo = periodo_str
                print(f"✓ Periodo recibido como literal: {periodo}")
        else:
            # Obtener periodo dinámicamente (priorizar activo)
            _, periodo = get_periodo_activo(db) or get_ultimo_periodo(db)
            if not periodo:
                return {"error": "No hay periodos configurados en el sistema."}
            print(f"⚠️ Periodo no proporcionado, usando periodo activo o último: {periodo}")
        
        # PRIORIDAD: Si vienen id_unidad_academica e id_nivel en el JSON (roles superiores),
        # usar esos valores. Si no, usar los de las cookies (roles normales)
        id_unidad_academica = data.get('id_unidad_academica')
        id_nivel = data.get('id_nivel')
        
        if id_unidad_academica is None:
            # No viene en JSON, usar cookie (roles 3-5)
            id_unidad_academica = int(sess.id_unidad_academica)
        else:
            # Viene en JSON (roles 6-9), convertir a int
            id_unidad_academica = int(id_unidad_academica)
        
        if id_nivel is None:
            # No viene en JSON, usar cookie (roles 3-5)
            id_nivel_cookie = sess.id_nivel
            if id_nivel_cookie == "None" or id_nivel_cookie is None or id_nivel_cookie == "":
                id_nivel = 0  # Valor por defecto
            else:
                id_nivel = int(id_nivel_cookie)
        else:
            # Viene en JSON (roles 6-9), convertir a int
            id_nivel = int(id_nivel)
        
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

        print(f"ID Unidad Académica: {id_unidad_academica} (de {'JSON' if data.get('id_unidad_academica') else 'cookie'})")
        print(f"ID Nivel: {id_nivel} (de {'JSON' if data.get('id_nivel') else 'cookie'})")
        print(f"Usuario: {nombre_completo}")

        # Obtener usuario y host para el SP
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        print(f"Host: {host_sp}")

        # Ejecutar SP y obtener metadatos (con usuario y host)
        rows_list, metadata, debug_msg, nota_rechazo = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=id_unidad_academica,
            id_nivel=id_nivel,
            periodo_input=periodo,
            default_periodo=None,  # Sin default, debe lanzar error si no existe
            usuario=usuario_sp,
            host=host_sp
        )
        
        print(f"\n=== RESULTADOS DEL SP ===")
        print(debug_msg)
        print(f"Total de filas: {len(rows_list)}")
        print(f"Metadatos extraídos: {metadata}")

        # Devolver resultado exitoso o error
        if "Error" in debug_msg:
            return {"error": debug_msg}
        else:
            return {
                "rows": rows_list,
                "metadata": metadata,
                "debug": debug_msg
            }

    except Exception as e:
        print(f"ERROR en endpoint SP: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error al obtener datos existentes: {str(e)}"}

# Endpoint para consulta dinámica de matrícula (roles superiores 6-9)
@router.post("/consultar_matricula_dinamica")
async def consultar_matricula_dinamica(
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Endpoint especial para roles superiores (6-9) que permite consultar
    la matrícula de cualquier UA y Nivel seleccionados.
    """
    try:
        data = await request.json()
        print(f"\n{'='*60}")
        print(f"CONSULTA DINÁMICA - Roles Superiores")
        print(f"{'='*60}")
        
        # Obtener parámetros de la solicitud
        id_unidad_academica_seleccionada = data.get('id_unidad_academica')
        id_nivel_seleccionado = data.get('id_nivel')
        id_periodo_input = data.get('id_periodo')  # Ahora recibe ID del periodo
        
        # Obtener periodo: convertir ID a literal o usar el activo/último dinámico
        if id_periodo_input:
            # Convertir ID de periodo a literal
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(id_periodo_input)).first()
            if periodo_obj:
                periodo = periodo_obj.Periodo
                print(f"✓ Periodo seleccionado: {periodo} (ID: {id_periodo_input})")
            else:
                return {"error": f"No se encontró el periodo con ID {id_periodo_input}"}
        else:
            # Si no se proporciona, usar periodo activo o último
            _, periodo = get_periodo_activo(db) or get_ultimo_periodo(db)
            if not periodo:
                return {"error": "No hay periodos configurados en el sistema."}
            print(f"⚠️ Periodo no especificado, usando periodo activo/último: {periodo}")
        
        # Validar rol del usuario (debe ser 4-9)
        id_rol = int(sess.id_rol)
        if id_rol not in [4, 5, 6, 7, 8, 9]:
            return {"error": "Acceso denegado. Solo roles de validación (4-9) pueden usar esta función."}
        
        # Obtener datos del usuario para auditoría
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        print(f"Usuario: {nombre_completo} (Rol ID: {id_rol})")
        print(f"UA seleccionada: {id_unidad_academica_seleccionada}")
        print(f"Nivel seleccionado: {id_nivel_seleccionado}")
        print(f"Período: {periodo}")
        
        # Validar que se hayan seleccionado UA y Nivel
        if not id_unidad_academica_seleccionada or not id_nivel_seleccionado:
            return {"error": "Debe seleccionar una Unidad Académica y un Nivel"}
        
        # Ejecutar SP con los parámetros seleccionados
        rows_list, metadata, debug_msg, nota_rechazo = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=int(id_unidad_academica_seleccionada),
            id_nivel=int(id_nivel_seleccionado),
            periodo_input=periodo,
            default_periodo=periodo,
            usuario=usuario_sp,
            host=host_sp
        )
        
        print(f"\n=== RESULTADOS ===")
        print(f"Total de filas: {len(rows_list)}")
        print(f"Debug: {debug_msg}")
        
        # Extraer metadatos únicos del SP
        metadata_extraido = extract_unique_values_from_sp(rows_list)
        
        # Obtener catálogos para mapear IDs
        grupos_edad_db = db.query(Grupo_Edad).all()
        tipos_ingreso_db = db.query(Tipo_Ingreso).all()
        programas_db = db.query(Programas).filter(Programas.Id_Nivel == int(id_nivel_seleccionado)).all()
        modalidades_db = db.query(Modalidad).all()
        semestres_db = db.query(Semestre).all()
        turnos_db = db.query(Turno).all()
        
        # Mapear SOLO los valores que devuelve el SP (no todos los del catálogo)
        def mapear_labels_a_objetos(labels, objetos_db, campo_label):
            mapa = {str(getattr(obj, campo_label)): obj for obj in objetos_db}
            resultado = []
            for label in labels:
                if label in mapa:
                    resultado.append(mapa[label])
            return resultado
        
        # Grupos de edad - solo del SP
        grupos_edad = mapear_labels_a_objetos(
            metadata_extraido.get('grupos_edad', []),
            grupos_edad_db,
            'Grupo_Edad'
        )
        
        # Tipos de ingreso - solo del SP
        tipos_ingreso = mapear_labels_a_objetos(
            metadata_extraido.get('tipos_ingreso', []),
            tipos_ingreso_db,
            'Tipo_de_Ingreso'
        )
        
        # Programas - solo del SP
        programas = mapear_labels_a_objetos(
            metadata_extraido.get('programas', []),
            programas_db,
            'Nombre_Programa'
        )
        
        # Modalidades - solo del SP
        modalidades = mapear_labels_a_objetos(
            metadata_extraido.get('modalidades', []),
            modalidades_db,
            'Modalidad'
        )
        
        # Semestres - solo del SP
        semestres = mapear_labels_a_objetos(
            metadata_extraido.get('semestres', []),
            semestres_db,
            'Semestre'
        )
        
        # Turnos - solo del SP
        turnos = mapear_labels_a_objetos(
            metadata_extraido.get('turnos', []),
            turnos_db,
            'Turno'
        )
        
        # Formatear para JSON
        grupos_edad_json = [{'Id_Grupo_Edad': g.Id_Grupo_Edad, 'Grupo_Edad': g.Grupo_Edad} for g in grupos_edad]
        tipos_ingreso_json = [{'Id_Tipo_Ingreso': t.Id_Tipo_Ingreso, 'Tipo_de_Ingreso': t.Tipo_de_Ingreso} for t in tipos_ingreso]
        programas_json = [{'Id_Programa': p.Id_Programa, 'Nombre_Programa': p.Nombre_Programa, 'Id_Semestre': p.Id_Semestre} for p in programas]
        modalidades_json = [{'Id_Modalidad': m.Id_Modalidad, 'Modalidad': m.Modalidad} for m in modalidades]
        semestres_json = [{'Id_Semestre': s.Id_Semestre, 'Semestre': s.Semestre} for s in semestres]
        turnos_json = [{'Id_Turno': t.Id_Turno, 'Turno': t.Turno} for t in turnos]
        
        print(f"📊 DEBUG: Pasando metadatos al frontend (todos del SP):")
        print(f"   - Grupos de edad: {len(grupos_edad_json)}")
        print(f"   - Tipos de ingreso: {len(tipos_ingreso_json)}")
        print(f"   - Turnos: {len(turnos_json)}")
        print(f"   - Programas: {len(programas_json)}")
        print(f"   - Modalidades: {len(modalidades_json)}")
        print(f"   - Semestres: {len(semestres_json)}")
        
        semestres_map = {s['Id_Semestre']: s['Semestre'] for s in semestres_json}
        
        # ========================================
        # VERIFICAR ESTADO DE VALIDACIÓN DEL USUARIO
        # ========================================
        
        # Obtener ID del periodo
        periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()
        if periodo_obj:
            periodo_id = periodo_obj.Id_Periodo
        else:
            periodo_id, _ = get_ultimo_periodo(db)
            if not periodo_id:
                periodo_id = 1  # Fallback solo si no hay periodos
        
        id_usuario_actual = int(sess.id_usuario)
        
        print(f"\n🔍 Verificando estado de validación para usuario {id_usuario_actual}...")
        
        # Verificar estado del semáforo de la UA seleccionada
        semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
            SemaforoUnidadAcademica.Id_Periodo == periodo_id,
            SemaforoUnidadAcademica.Id_Unidad_Academica == int(id_unidad_academica_seleccionada),
            SemaforoUnidadAcademica.Id_Nivel == int(id_nivel_seleccionado),
            SemaforoUnidadAcademica.Id_Formato == 1  # Formato de matrícula
        ).first()
        
        usuario_ya_valido = False
        usuario_ya_rechazo = False
        puede_validar = False
        matricula_rechazada = False
        rechazo_info = None
        
        if semaforo_unidad:
            estado_semaforo = semaforo_unidad.Id_Semaforo
            print(f"   📊 Estado del semáforo: {estado_semaforo}")
            
            # Lógica: El usuario puede validar si el semáforo está en (id_rol - 1)
            semaforo_esperado = id_rol - 1
            print(f"   ⚖️ Semáforo esperado para rol {id_rol}: {semaforo_esperado}")
            
            if estado_semaforo == semaforo_esperado:
                puede_validar = True
                print(f"   ✅ Usuario PUEDE validar (semáforo en nivel correcto)")
            elif estado_semaforo >= id_rol:
                usuario_ya_valido = True
                print(f"   🔒 Usuario YA validó (semáforo >= {id_rol})")
            else:
                print(f"   ⏳ Usuario debe esperar (semáforo en nivel {estado_semaforo})")
        else:
            print(f"   ⚠️ No se encontró semáforo para esta UA/Nivel/Periodo")
        
        # Verificar si el usuario rechazó esta matrícula
        validacion_rechazo = db.query(Validacion).filter(
            Validacion.Id_Periodo == periodo_id,
            Validacion.Id_Usuario == id_usuario_actual,
            Validacion.Id_Formato == 1,
            Validacion.Validado == 0  # Rechazo
        ).first()
        
        if validacion_rechazo:
            if not (semaforo_unidad and estado_semaforo == (id_rol - 1)):
                usuario_ya_rechazo = True
                print(f"   ❌ Usuario YA rechazó esta matrícula")
        
        # Verificar si existe algún rechazo activo en esta UA
        from backend.database.models.Usuario import Usuario
        ultimo_rechazo = (
            db.query(Validacion)
            .join(Usuario, Usuario.Id_Usuario == Validacion.Id_Usuario)
            .filter(
                Validacion.Id_Periodo == periodo_id,
                Validacion.Id_Formato == 1,
                Validacion.Validado == 0,
                Usuario.Id_Unidad_Academica == int(id_unidad_academica_seleccionada)
            )
            .order_by(Validacion.Fecha.desc())
            .first()
        )
        
        if ultimo_rechazo:
            matricula_rechazada = True
            usuario_rechazo = db.query(Usuario).filter(
                Usuario.Id_Usuario == ultimo_rechazo.Id_Usuario
            ).first()
            
            nombre_rechazo = "Validador"
            if usuario_rechazo:
                nombre_rechazo = f"{usuario_rechazo.Nombre} {usuario_rechazo.Paterno} {usuario_rechazo.Materno}".strip()
            
            # Obtener info de UA
            ua_info = db.query(Unidad_Academica).filter(
                Unidad_Academica.Id_Unidad_Academica == int(id_unidad_academica_seleccionada)
            ).first()
            
            rechazo_info = {
                'motivo': nota_rechazo if nota_rechazo else (ultimo_rechazo.Nota or "Sin especificar motivo"),
                'rechazado_por': nombre_rechazo,
                'fecha': ultimo_rechazo.Fecha.strftime("%d/%m/%Y %H:%M") if ultimo_rechazo.Fecha else "",
                'periodo': periodo,
                'unidad': ua_info.Nombre if ua_info else ""
            }
            print(f"   📋 Matrícula rechazada - Motivo: {rechazo_info['motivo'][:50]}...")
        
        print(f"\n📤 Estado final:")
        print(f"   puede_validar: {puede_validar}")
        print(f"   usuario_ya_valido: {usuario_ya_valido}")
        print(f"   usuario_ya_rechazo: {usuario_ya_rechazo}")
        print(f"   matricula_rechazada: {matricula_rechazada}")
        
        # Devolver datos estructurados con información de validación
        return {
            "success": True,
            "rows": rows_list,
            "metadata": {
                "grupos_edad": grupos_edad_json,
                "tipos_ingreso": tipos_ingreso_json,
                "programas": programas_json,
                "modalidades": modalidades_json,
                "semestres": semestres_json,
                "turnos": turnos_json,
                "semestres_map": semestres_map
            },
            "validacion_estado": {
                "puede_validar": puede_validar,
                "usuario_ya_valido": usuario_ya_valido,
                "usuario_ya_rechazo": usuario_ya_rechazo,
                "matricula_rechazada": matricula_rechazada,
                "rechazo_info": rechazo_info,
                "id_rol": id_rol,
                "id_unidad_academica": int(id_unidad_academica_seleccionada),
                "id_nivel": int(id_nivel_seleccionado)
            },
            "debug": debug_msg
        }
        
    except Exception as e:
        print(f"ERROR en consulta dinámica: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error al consultar matrícula: {str(e)}"}

# Endpoint para vista de resumen ejecutivo (roles superiores 6-9)
@router.get('/resumen')
async def resumen_matricula_roles_superiores(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Vista de resumen ejecutivo de matrícula para roles superiores (6-9).
    Muestra tablas consolidadas por programa académico con todas las dimensiones.
    """
    try:
        # Validar que el usuario sea rol validador o superior (4-9)
        id_rol = int(sess.id_rol)
        if id_rol not in [4, 5, 6, 7, 8, 9]:
            raise HTTPException(status_code=403, detail="Acceso denegado. Solo roles de validación y superiores (4-9) pueden ver esta vista.")
        
        # Obtener datos del usuario
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        nombre_rol = sess.nombre_rol
        
        # Obtener parámetros de consulta
        id_unidad_academica = request.query_params.get('ua')
        id_nivel = request.query_params.get('nivel')
        id_periodo_input = request.query_params.get('id_periodo')  # Ahora recibe ID del periodo
        
        # Convertir ID de periodo a literal si se proporciona
        if id_periodo_input:
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(id_periodo_input)).first()
            if periodo_obj:
                periodo = periodo_obj.Periodo
                print(f"✓ Periodo seleccionado para resumen: {periodo} (ID: {id_periodo_input})")
            else:
                raise HTTPException(status_code=400, detail=f"No se encontró el periodo con ID {id_periodo_input}")
        else:
            # Si no se proporciona, usar periodo activo o último
            _, periodo = get_periodo_activo(db) or get_ultimo_periodo(db)
            if not periodo:
                raise HTTPException(status_code=400, detail="No hay periodos configurados en el sistema")
            print(f"⚠️ Periodo no especificado para resumen, usando activo/último: {periodo}")
        
        if not id_unidad_academica or not id_nivel:
            raise HTTPException(status_code=400, detail="Debe especificar UA y Nivel")
        
        print(f"\n{'='*60}")
        print(f"RESUMEN EJECUTIVO DE MATRÍCULA - Roles Superiores")
        print(f"Usuario: {nombre_completo} (Rol: {nombre_rol})")
        print(f"UA: {id_unidad_academica}, Nivel: {id_nivel}, Período: {periodo}")
        print(f"{'='*60}")
        
        # Obtener datos del SP
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        rows_sp, metadata_sp, debug_msg_sp, nota_rechazo_sp = execute_matricula_sp_with_context(
            db=db,
            id_unidad_academica=int(id_unidad_academica),
            id_nivel=int(id_nivel),
            periodo_input=periodo,
            default_periodo=periodo,
            usuario=usuario_sp,
            host=host_sp
        )
        
        print(f"📊 Total de registros del SP: {len(rows_sp)}")
        
        # Debug: mostrar primeras filas
        if len(rows_sp) > 0:
            print(f"🔍 Primera fila del SP: {rows_sp[0]}")
            print(f"🔍 Keys disponibles: {list(rows_sp[0].keys()) if rows_sp else 'Sin datos'}")
        else:
            print("⚠️ SP no retornó datos!")
        
        # Procesar datos para el resumen
        resumen_por_programa = {}
        
        for row in rows_sp:
            # Obtener nombre del programa - intentar ambos nombres de columna
            programa = row.get('Nombre_Programa') or row.get('Programa') or 'Sin Programa'
            semestre = row.get('Semestre', 'N/A')
            turno = row.get('Turno', 'N/A')
            modalidad = row.get('Modalidad', 'N/A')
            grupo_edad = row.get('Grupo_Edad', 'N/A')
            tipo_ingreso = row.get('Tipo_de_Ingreso', 'N/A')
            sexo = row.get('Sexo', '').strip()
            # La columna del SP se llama 'Matricula', no 'Cantidad'
            cantidad = row.get('Matricula', 0) or 0
            
            # Determinar si es hombre o mujer (el SP retorna 'Hombre'/'Mujer')
            hombres = cantidad if sexo in ['Masculino', 'Hombre'] else 0
            mujeres = cantidad if sexo in ['Femenino', 'Mujer'] else 0
            
            # Inicializar programa si no existe
            if programa not in resumen_por_programa:
                resumen_por_programa[programa] = {
                    'semestre_turno_modalidad': {},
                    'grupos_edad': {},
                    'tipos_ingreso': {},
                    'total_hombres': 0,
                    'total_mujeres': 0
                }
            
            # Agrupar por Semestre/Turno/Modalidad
            clave_stm = f"{semestre}|{turno}|{modalidad}"
            if clave_stm not in resumen_por_programa[programa]['semestre_turno_modalidad']:
                resumen_por_programa[programa]['semestre_turno_modalidad'][clave_stm] = {
                    'semestre': semestre,
                    'turno': turno,
                    'modalidad': modalidad,
                    'hombres': 0,
                    'mujeres': 0
                }
            resumen_por_programa[programa]['semestre_turno_modalidad'][clave_stm]['hombres'] += hombres
            resumen_por_programa[programa]['semestre_turno_modalidad'][clave_stm]['mujeres'] += mujeres
            
            # Agrupar por Grupo de Edad
            if grupo_edad not in resumen_por_programa[programa]['grupos_edad']:
                resumen_por_programa[programa]['grupos_edad'][grupo_edad] = {
                    'hombres': 0,
                    'mujeres': 0
                }
            resumen_por_programa[programa]['grupos_edad'][grupo_edad]['hombres'] += hombres
            resumen_por_programa[programa]['grupos_edad'][grupo_edad]['mujeres'] += mujeres
            
            # Agrupar por Tipo de Ingreso
            if tipo_ingreso not in resumen_por_programa[programa]['tipos_ingreso']:
                resumen_por_programa[programa]['tipos_ingreso'][tipo_ingreso] = {
                    'hombres': 0,
                    'mujeres': 0
                }
            resumen_por_programa[programa]['tipos_ingreso'][tipo_ingreso]['hombres'] += hombres
            resumen_por_programa[programa]['tipos_ingreso'][tipo_ingreso]['mujeres'] += mujeres
            
            # Totales por programa
            resumen_por_programa[programa]['total_hombres'] += hombres
            resumen_por_programa[programa]['total_mujeres'] += mujeres
        
        # Convertir a listas ordenadas para el template
        for programa in resumen_por_programa:
            resumen_por_programa[programa]['semestre_turno_modalidad'] = sorted(
                resumen_por_programa[programa]['semestre_turno_modalidad'].values(),
                key=lambda x: (x['semestre'], x['turno'], x['modalidad'])
            )
            resumen_por_programa[programa]['grupos_edad_list'] = sorted(
                [{'grupo': k, **v} for k, v in resumen_por_programa[programa]['grupos_edad'].items()],
                key=lambda x: x['grupo']
            )
            resumen_por_programa[programa]['tipos_ingreso_list'] = sorted(
                [{'tipo': k, **v} for k, v in resumen_por_programa[programa]['tipos_ingreso'].items()],
                key=lambda x: x['tipo']
            )
        
        # Calcular totales generales
        total_general_hombres = sum(p['total_hombres'] for p in resumen_por_programa.values())
        total_general_mujeres = sum(p['total_mujeres'] for p in resumen_por_programa.values())
        
        # Convertir a lista ordenada alfabéticamente por nombre de programa
        programas_ordenados = [
            {'nombre': programa, 'datos': datos}
            for programa, datos in sorted(resumen_por_programa.items())
        ]
        
        # Obtener información de UA y Nivel para el encabezado
        unidad_academica = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == int(id_unidad_academica)
        ).first()
        
        nivel_obj = db.query(Nivel).filter(
            Nivel.Id_Nivel == int(id_nivel)
        ).first()
        
        print(f"✅ Resumen generado: {len(resumen_por_programa)} programas")
        print(f"📈 Total general: {total_general_hombres} H + {total_general_mujeres} M = {total_general_hombres + total_general_mujeres}")
        
        # VERIFICAR SI EL USUARIO ACTUAL YA VALIDÓ/RECHAZÓ
        usuario_ya_valido = False
        usuario_ya_rechazo = False
        
        # Solo verificar para roles validadores (6-9)
        if id_rol in [6, 7, 8, 9]:
            print(f"\n🔍 Verificando si el usuario (ID: {request.cookies.get('id_usuario')}) ya validó/rechazó...")
            print(f"   Rol del usuario: {id_rol}")
            
            # Obtener el ID del período
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()
            periodo_id = periodo_obj.Id_Periodo if periodo_obj else None
            
            if periodo_id:
                # Obtener el estado del semáforo general de la unidad académica
                semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
                    SemaforoUnidadAcademica.Id_Periodo == periodo_id,
                    SemaforoUnidadAcademica.Id_Unidad_Academica == int(id_unidad_academica),
                    SemaforoUnidadAcademica.Id_Formato == 1  # Formato de matrícula
                ).first()
                
                if semaforo_unidad:
                    estado_semaforo = semaforo_unidad.Id_Semaforo
                    print(f"   Estado del semáforo: {estado_semaforo}")
                    
                    # LÓGICA: El usuario puede validar si el semáforo está en (id_rol - 1)
                    semaforo_esperado = id_rol - 1
                    print(f"   Semáforo esperado para que rol {id_rol} valide: {semaforo_esperado}")
                    
                    if estado_semaforo == semaforo_esperado:
                        print(f"✅ Semáforo en nivel correcto ({estado_semaforo}) - Usuario puede validar")
                        usuario_ya_valido = False
                        usuario_ya_rechazo = False
                    elif estado_semaforo >= id_rol:
                        print(f"🔒 Semáforo ya en nivel {estado_semaforo} (>= {id_rol}) - Usuario ya validó")
                        usuario_ya_valido = True
                    elif estado_semaforo < semaforo_esperado:
                        print(f"⏳ Semáforo en nivel {estado_semaforo} (< {semaforo_esperado}) - Usuario debe esperar")
                        usuario_ya_valido = False
                        usuario_ya_rechazo = False
                else:
                    print(f"⚠️ No se encontró semáforo para esta UA/Periodo")
                
                # Verificar si el usuario rechazó
                id_usuario_actual = int(sess.id_usuario)
                validacion_rechazo = db.query(Validacion).filter(
                    Validacion.Id_Periodo == periodo_id,
                    Validacion.Id_Usuario == id_usuario_actual,
                    Validacion.Id_Formato == 1,
                    Validacion.Validado == 0  # Solo rechazos
                ).first()
                
                if validacion_rechazo and not (semaforo_unidad and estado_semaforo == (id_rol - 1)):
                    usuario_ya_rechazo = True
                    print(f"❌ Usuario YA RECHAZÓ esta matrícula (Fecha: {validacion_rechazo.Fecha})")
        
        print(f"   usuario_ya_valido = {usuario_ya_valido}")
        print(f"   usuario_ya_rechazo = {usuario_ya_rechazo}")
        
        return templates.TemplateResponse(
            "matricula_resumen_superior.html",
            {
                "request": request,
                "nombre_usuario": nombre_completo,
                "nombre_rol": nombre_rol,
                "id_rol": id_rol,
                "unidad_academica": unidad_academica,
                "nivel": nivel_obj,
                "periodo": periodo,
                "programas_ordenados": programas_ordenados,
                "total_general_hombres": total_general_hombres,
                "total_general_mujeres": total_general_mujeres,
                "total_general": total_general_hombres + total_general_mujeres,
                "usuario_ya_valido": usuario_ya_valido,
                "usuario_ya_rechazo": usuario_ya_rechazo
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR en resumen ejecutivo: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al generar resumen: {str(e)}")

# Endpoint de depuración detallada del SP
@router.get('/debug_sp')
async def debug_sp(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """Endpoint de depuración que usa el servicio (sin SQL crudo aquí)."""
    try:
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)

        # Obtener periodo dinámicamente (priorizar activo)
        _, periodo = get_periodo_activo(db) or get_ultimo_periodo(db)
        if not periodo:
            return {"error": "No hay periodos configurados en el sistema."}
        
        rows, metadata, debug_msg, nota_rechazo = execute_matricula_sp_with_context(
            db,
            id_unidad_academica,
            id_nivel,
            periodo,
            None,  # Sin default
            usuario_sp,
            host_sp,
        )
        columnas = list(rows[0].keys()) if rows else []
        return {
            "mensaje": debug_msg,
            "total_filas": len(rows),
            "columnas": columnas,
            "primera_fila": rows[0] if rows else None,
            "metadata": metadata,
        }
    except Exception as e:
        return {"error": str(e)}

@router.get('/semestres_map')
async def semestres_map_sp(db: Session = Depends(get_db)):
    """Endpoint para obtener el mapeo de semestres (Id -> Nombre)"""
    try:
        semestres = db.query(Semestre).all()
        semestres_map = {s.Id_Semestre: s.Semestre for s in semestres}
        return semestres_map
    except Exception as e:
        return {"error": str(e)}

@router.post("/guardar_captura_completa")
async def guardar_captura_completa(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Guardar la captura completa de matrícula enviada desde el frontend.
    Convierte el formato del frontend al modelo Temp_Matricula.
    """
    try:
        data = await request.json()
        print(f"\n=== GUARDANDO CAPTURA COMPLETA ===")
        print(f"Datos recibidos: {data}")
        
        # Obtener datos del usuario desde cookies
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        # Obtener usuario y host
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        # Extraer información base
        periodo_input = data.get('periodo')
        programa = data.get('programa')
        semestre = data.get('semestre')
        modalidad = data.get('modalidad')
        turno = data.get('turno')
        total_grupos = data.get('total_grupos')
        datos_matricula = data.get('datos_matricula', {})
        
        # Convertir período de ID a formato literal para guardar en Temp_Matricula
        if periodo_input:
            if str(periodo_input).isdigit():
                # Buscar el período por ID
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_input)).first()
                if periodo_obj:
                    periodo = periodo_obj.Periodo  # '2025-2026/1'
                
                    print(f"🔄 Período convertido de ID {periodo_input} → '{periodo}' para Temp_Matricula")
                else:
                    print(f"⚠️ ID de período {periodo_input} no encontrado, usando último periodo")
                    _, periodo = get_ultimo_periodo(db)
                    if not periodo:
                        raise HTTPException(status_code=400, detail="No se pudo obtener un periodo válido")
            else:
                # Ya es formato literal
                periodo = str(periodo_input)
                print(f"✅ Período ya en formato literal: '{periodo}'")
        else:
            _, periodo = get_ultimo_periodo(db)
            if not periodo:
                raise HTTPException(status_code=400, detail="No se pudo obtener un periodo válido")
            print(f"📌 Usando último período: '{periodo}'")
        
        if not datos_matricula:
            return {"error": "No se encontraron datos de matrícula para guardar"}
        
        # Obtener campos válidos del modelo Temp_Matricula
        valid_fields = set(Temp_Matricula.__annotations__.keys())
        print(f"Campos válidos Temp_Matricula: {valid_fields}")
        
        # Obtener nombres desde la base de datos para mapear IDs
        programa_obj = db.query(Programas).filter(Programas.Id_Programa == int(programa)).first()
        modalidad_obj = db.query(Modalidad).filter(Modalidad.Id_Modalidad == int(modalidad)).first()
        turno_obj = db.query(Turno).filter(Turno.Id_Turno == int(turno)).first()
        semestre_obj = db.query(Semestre).filter(Semestre.Id_Semestre == int(semestre)).first()
        
        # Obtener Nombre_Rama desde el programa
        rama_obj = None
        if programa_obj and programa_obj.Id_Rama_Programa:
            rama_obj = db.query(Rama).filter(Rama.Id_Rama == programa_obj.Id_Rama_Programa).first()
        
        # Si el programa es "Tronco Común", usar rama por defecto 
        #Revisar que la Rama a la que pertenezca este con el Estatus = 1 (Activa), sino el SP no funciona
        if programa_obj and 'tronco común' in programa_obj.Nombre_Programa.lower():
            print(f"🎓 Programa 'Tronco Común' detectado - Usando rama por defecto")
            rama_default = db.query(Rama).filter(
                Rama.Nombre_Rama == 'Ingeniería y Ciencias Físico Matemáticas'
            ).first()
            if rama_default:
                rama_obj = rama_default
                print(f"✅ Rama por defecto asignada: {rama_obj.Nombre_Rama}")
            else:
                print(f"⚠️ Rama 'Ingeniería y Ciencias Físico Matemáticas' no encontrada en BD")
        
        #Si el programa es "Propedeútico", usar rama por defecto
        if programa_obj and 'propedeútico' in programa_obj.Nombre_Programa.lower():
            print(f"🎓 Programa 'Propedeútico' detectado - Usando rama por defecto")
            rama_default = db.query(Rama).filter(
                Rama.Nombre_Rama == 'Ingeniería y Ciencias Físico Matemáticas'
            ).first()
            if rama_default:
                rama_obj = rama_default
                print(f"✅ Rama por defecto asignada: {rama_obj.Nombre_Rama}")
            else:
                print(f"⚠️ Rama 'Ingeniería y Ciencias Físico Matemáticas' no encontrada en BD")

        # Obtener sigla de la unidad académica y nivel desde cookies
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        
        unidad_obj = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        
        nivel_obj = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        
        # Obtener mapeos de grupos de edad y tipos de ingreso para convertir a nombres
        grupos_edad_db = db.query(Grupo_Edad).all()
        grupos_edad_map = {str(g.Id_Grupo_Edad): g.Grupo_Edad for g in grupos_edad_db}
        
        tipos_ingreso_db = db.query(Tipo_Ingreso).all()
        tipos_ingreso_map = {str(t.Id_Tipo_Ingreso): t.Tipo_de_Ingreso for t in tipos_ingreso_db}
        
        registros_insertados = 0
        registros_rechazados = 0
        
        # Limpiar la sesión para evitar conflictos de identidad
        db.expunge_all()

        # Limpieza preventiva: eliminar TODOS los registros anteriores para este
        # (Sigla, Periodo, Programa, Semestre, Turno) SIN importar la modalidad.
        # Esto evita que el SP procese datos de guardados previos de otras modalidades.
        if unidad_obj and programa_obj and semestre_obj and turno_obj:
            eliminados_prev = db.query(Temp_Matricula).filter(
                Temp_Matricula.Sigla       == unidad_obj.Sigla,
                Temp_Matricula.Periodo     == periodo,
                Temp_Matricula.Nombre_Programa == programa_obj.Nombre_Programa,
                Temp_Matricula.Semestre    == semestre_obj.Semestre,
                Temp_Matricula.Turno       == turno_obj.Turno,
            ).delete(synchronize_session=False)
            print(f"🧹 Pre-limpieza Temp_Matricula: {eliminados_prev} registros eliminados "
                  f"(programa='{programa_obj.Nombre_Programa}', semestre='{semestre_obj.Semestre}', "
                  f"turno='{turno_obj.Turno}') — solo se conservará la modalidad actual")

        # Obtener el semestre seleccionado como número
        semestre_numero = None
        if semestre_obj:
            try:
                # Extraer el número del semestre (ej: "1" de "Primer Semestre", "2" de "Segundo Semestre")
                semestre_text = semestre_obj.Semestre.lower()
                if "primer" in semestre_text or semestre_text == "1":
                    semestre_numero = 1
                elif "segundo" in semestre_text or semestre_text == "2":
                    semestre_numero = 2
                elif "tercer" in semestre_text or semestre_text == "3":
                    semestre_numero = 3
                # Agregar más semestres según sea necesario
            except:
                pass
        
        print(f"Semestre detectado: {semestre_numero} (de: {semestre_obj.Semestre if semestre_obj else 'N/A'})")
        
        # Procesar cada registro de matrícula
        for key, dato in datos_matricula.items():
            # Validación de reglas de semestre - SEGURIDAD BACKEND
            tipo_ingreso_id = str(dato.get('tipo_ingreso', ''))
            
            # Aplicar reglas de validación por semestre
            if semestre_numero is not None and tipo_ingreso_id:
                # Regla 1: Semestre 1 no puede tener "Reingreso" (ID: 2)
                if semestre_numero == 1 and tipo_ingreso_id == "2":
                    print(f"VALIDACIÓN RECHAZADA: Semestre 1 no puede tener Reingreso (tipo_ingreso: {tipo_ingreso_id})")
                    registros_rechazados += 1
                    continue  # Saltar este registro
                
                # Regla 2: Semestres diferentes a 1 no pueden tener "Nuevo Ingreso" (ID: 1)
                if semestre_numero != 1 and tipo_ingreso_id == "1":
                    print(f"VALIDACIÓN RECHAZADA: Semestre {semestre_numero} no puede tener Nuevo Ingreso (tipo_ingreso: {tipo_ingreso_id})")
                    registros_rechazados += 1
                    continue  # Saltar este registro
            
            # Mapear grupo_edad ID a nombre completo
            grupo_edad_id = str(dato.get('grupo_edad', ''))
            grupo_edad_nombre = grupos_edad_map.get(grupo_edad_id, grupo_edad_id)
            
            # Mapear tipo_ingreso ID a nombre completo
            tipo_ingreso_nombre = tipos_ingreso_map.get(tipo_ingreso_id, tipo_ingreso_id)
            
            # Convertir sexo de M/F a Hombre/Mujer
            sexo_corto = dato.get('sexo', '')
            if sexo_corto == 'M':
                sexo_completo = 'Hombre'
            elif sexo_corto == 'F':
                sexo_completo = 'Mujer'
            else:
                sexo_completo = sexo_corto
            
            # Construir registro para Temp_Matricula
            registro = {
                'Periodo': periodo,
                'Sigla': unidad_obj.Sigla if unidad_obj else 'UNK',
                'Nombre_Programa': programa_obj.Nombre_Programa if programa_obj else '',
                'Nombre_Rama': rama_obj.Nombre_Rama if rama_obj else 'NULL',
                'Nivel': nivel_obj.Nivel if nivel_obj else '',
                'Modalidad': modalidad_obj.Modalidad if modalidad_obj else '',
                'Turno': turno_obj.Turno if turno_obj else '',
                'Semestre': semestre_obj.Semestre if semestre_obj else '',
                'Grupo_Edad': grupo_edad_nombre,
                'Tipo_Ingreso': tipo_ingreso_nombre,
                'Sexo': sexo_completo,
                'Matricula': int(dato.get('matricula', 0)),
                'Salones': int(dato.get('salones', total_grupos))
            }
            
            # Filtrar solo campos válidos
            filtered = {k: v for k, v in registro.items() if k in valid_fields}

            # Cambiar condición para incluir valores de 0 (>= 0 en lugar de > 0)
            if filtered and filtered.get('Matricula', 0) >= 0:
                # Clave lógica para identificar un registro único en Temp_Matricula
                # (sin incluir Matricula ni Salones)
                filtro_unico = {k: v for k, v in filtered.items() if k not in ['Matricula', 'Salones']}

                # Eliminar cualquier registro previo que coincida con esta clave
                # Esto evita problemas de múltiples filas coincidiendo en un UPDATE (StaleDataError)
                if filtro_unico:
                    db.query(Temp_Matricula).filter_by(**filtro_unico).delete(synchronize_session=False)

                # Insertar el nuevo registro con la matrícula y salones actuales
                temp_matricula = Temp_Matricula(**filtered)
                

                #Descomentar en dado caso de querer guardar solo en Temp_Matrícula
                #print(f"\n📊 DATOS A GUARDAR EN Temp_Matricula: {filtered}")
                #input("⏸️  PAUSA - Presiona Enter para continuar...")
                
                db.add(temp_matricula)

                registros_insertados += 1
                print(f"Registro procesado (upsert lógico): {filtered}")
        
        db.commit()
        
        # Construir mensaje informativo
        mensaje_base = f"Matrícula procesada. {registros_insertados} registros guardados"
        if registros_rechazados > 0:
            mensaje_base += f", {registros_rechazados} registros rechazados por validación de semestre"
        mensaje_base += "."
        
        return {
            "mensaje": mensaje_base,
            "registros_insertados": registros_insertados,
            "registros_rechazados": registros_rechazados,
            "validacion_aplicada": semestre_numero is not None
        }
        
    except Exception as e:
        db.rollback()
        print(f"ERROR al guardar captura completa: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al guardar la matrícula: {str(e)}")

@router.post("/guardar_progreso")
def guardar_progreso(datos: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Guardar el progreso de la matrícula en la tabla Temp_Matricula.
    Args:
        datos: Lista de diccionarios con los datos de la matrícula.
        db: Sesión de base de datos.
    Returns:
        Mensaje de éxito o error.
    """
    try:
        # Obtener campos válidos desde el modelo Temp_Matricula
        valid_fields = set()
        # Intentar leer anotaciones (Python typing) si están presentes
        try:
            valid_fields = set(Temp_Matricula.__annotations__.keys())
        except Exception:
            # Fallback: leer atributos públicos definidos en la clase
            valid_fields = {k for k in dir(Temp_Matricula) if not k.startswith('_')}

        print(f"Campos válidos Temp_Matricula: {valid_fields}")

        # Limpiar la sesión para evitar conflictos de identidad
        db.expunge_all()

        for dato in datos:
            # Filtrar solo las claves que estén en el modelo
            filtered = {k: v for k, v in dato.items() if k in valid_fields}
            if not filtered:
                # Si no hay campos válidos, saltar
                print(f"Advertencia: entrada sin campos válidos será ignorada: {dato}")
                continue
            
            # Usar merge() para manejar automáticamente INSERT/UPDATE
            temp_matricula = Temp_Matricula(**filtered)
            merged_obj = db.merge(temp_matricula)
            print(f"Registro procesado (merge) en guardar_progreso: {filtered}")

        db.commit()
        return {"message": "Progreso guardado exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el progreso: {str(e)}")

@router.post("/actualizar_matricula")
async def actualizar_matricula(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Ejecuta el SP SP_Actualiza_Matricula_Por_Unidad_Academica para actualizar 
    la tabla Matricula con los datos de Temp_Matricula y luego limpiar la tabla temporal.
    """
    try:
        # Obtener datos del usuario desde cookies
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
        
        # Obtener unidad académica desde cookies (si no está, resolver vía Id_Unidad_Academica)
        unidad_sigla = request.cookies.get("unidad_sigla", "")
        if not unidad_sigla:
            try:
                id_unidad_cookie = int(sess.id_unidad_academica)
            except Exception:
                id_unidad_cookie = 0
            if id_unidad_cookie:
                unidad_obj = db.query(Unidad_Academica).filter(Unidad_Academica.Id_Unidad_Academica == id_unidad_cookie).first()
                if unidad_obj and unidad_obj.Sigla:
                    unidad_sigla = unidad_obj.Sigla
                    print(f"🛠️ Resuelta unidad_sigla desde Id_Unidad_Academica cookie: {unidad_sigla}")
                else:
                    print("⚠️ No se pudo resolver unidad_sigla desde Id_Unidad_Academica")
            else:
                print("⚠️ Cookie unidad_sigla ausente y no hay Id_Unidad_Academica válido")

        # Obtener usuario y host
        usuario_sp = nombre_completo or 'sistema'
        host_sp = get_request_host(request)
        
        # Obtener período y total_grupos desde el request o usar valores por defecto
        data = await request.json()
        periodo_input = data.get('periodo')
        total_grupos = data.get('total_grupos', 0)
        
        # SIEMPRE convertir a formato literal para el SP
        if periodo_input:
            # Si es un ID numérico (como '7'), convertir a literal
            if str(periodo_input).isdigit():
                # Buscar el período por ID en la base de datos
                periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_input)).first()
                if periodo_obj:
                    periodo = periodo_obj.Periodo  # '2025-2026/1'
                
                    print(f"🔄 Convertido ID {periodo_input} → '{periodo}'")
                else:
                    print(f"⚠️ ID de período {periodo_input} no encontrado, usando último periodo")
                    _, periodo = get_ultimo_periodo(db)
                    if not periodo:
                        raise HTTPException(status_code=400, detail="No se pudo obtener un periodo válido")
            else:
                # Ya es formato literal, usarlo directamente
                periodo = str(periodo_input)
                print(f"✅ Período ya en formato literal: '{periodo}'")
        else:
            # No viene período, usar el último periodo disponible
            _, periodo = get_ultimo_periodo(db)
            if not periodo:
                raise HTTPException(status_code=400, detail="No se pudo obtener un periodo válido")
            print(f"📌 Usando último período: '{periodo}'")
            
        # Obtener y validar el nivel desde la sesión
        nivel = sess.nombre_nivel
        
        # Validar que el nivel existe y es válido
        if not nivel or not str(nivel).strip():
            raise HTTPException(
                status_code=400, 
                detail="Nivel no disponible en la sesión. Por favor, vuelva a iniciar sesión."
            )
        
        # Limpiar el nivel (quitar espacios, normalizar)
        nivel = str(nivel).strip()
        
        # Verificar que el nivel existe en la BD
        nivel_obj = db.query(Nivel).filter(
            Nivel.Nivel == nivel,
            Nivel.Id_Estatus == 1
        ).first()
        
        if not nivel_obj:
            raise HTTPException(
                status_code=400,
                detail=f"El nivel '{nivel}' no existe o está inactivo en la base de datos."
            )
        
        print(f"✅ Nivel validado: '{nivel}' (ID: {nivel_obj.Id_Nivel})")
        
        if not periodo:
            raise HTTPException(status_code=400, detail="Período es requerido para actualizar la matrícula")
        
        print(f"\n=== ACTUALIZANDO MATRÍCULA ===")
        print(f"Usuario: {usuario_sp}")
        print(f"Período: {periodo}")
        print(f"Host: {host_sp}")
        print(f"Nivel: {nivel}")
        print(f"ID Nivel desde cookies: {request.cookies.get('id_nivel', 'No encontrado')}")
        print(f"Nombre Nivel desde cookies: {request.cookies.get('nombre_nivel', 'No encontrado')}")
        print(f"Cookies disponibles: {list(request.cookies.keys())}")
        
        # Verificar que hay datos en Temp_Matricula antes de actualizar
        temp_count = db.query(Temp_Matricula).count()
        if temp_count == 0:
            return {
                "warning": "No hay datos en Temp_Matricula para actualizar",
                "registros_temp": 0,
                "registros_actualizados": 0
            }
        
        print(f"Registros en Temp_Matricula: {temp_count}")
        
        # DIAGNÓSTICO: Mostrar contenido de Temp_Matricula antes de actualizar
        print(f"\n=== DIAGNÓSTICO TEMP_MATRICULA ===")
        temp_records = db.query(Temp_Matricula).all()
        for i, record in enumerate(temp_records, 1):
            print(f"Registro {i}:")
            print(f"  Periodo: '{record.Periodo}'")
            print(f"  Sigla: '{record.Sigla}'")
            print(f"  Nombre_Programa: '{record.Nombre_Programa}'")
            print(f"  Nombre_Rama: '{record.Nombre_Rama}'")
            print(f"  Nivel: '{record.Nivel}'")
            print(f"  Modalidad: '{record.Modalidad}'")
            print(f"  Turno: '{record.Turno}'")
            print(f"  Semestre: '{record.Semestre}'")
            print(f"  Grupo_Edad: '{record.Grupo_Edad}'")
            print(f"  Tipo_Ingreso: '{record.Tipo_Ingreso}'")
            print(f"  Sexo: '{record.Sexo}'")
            print(f"  Matricula: {record.Matricula}")
            print("-" * 40)
        
        # DIAGNÓSTICO: Verificar si existen registros en Matricula que coincidan
        print(f"\n=== VERIFICANDO COINCIDENCIAS EN MATRICULA ===")
        matricula_count = db.query(Matricula).count()
        print(f"Total registros en Matricula: {matricula_count}")
        
        # Buscar un registro de ejemplo para ver si hay coincidencias
        if temp_records:
            temp_ejemplo = temp_records[0]
            print(f"\nBuscando coincidencias para el primer registro de Temp_Matricula:")
            
            # Verificar periodo
            periodo_match = db.query(Periodo).filter(Periodo.Periodo == temp_ejemplo.Periodo).first()
            print(f"Periodo '{temp_ejemplo.Periodo}' encontrado: {periodo_match is not None}")
            if periodo_match:
                print(f"  ID Periodo: {periodo_match.Id_Periodo}")
            
            # Verificar unidad académica
            unidad_match = db.query(Unidad_Academica).filter(Unidad_Academica.Sigla == temp_ejemplo.Sigla).first()
            print(f"Unidad '{temp_ejemplo.Sigla}' encontrada: {unidad_match is not None}")
            if unidad_match:
                print(f"  ID Unidad: {unidad_match.Id_Unidad_Academica}")
            
            # Verificar programa
            programa_match = db.query(Programas).filter(Programas.Nombre_Programa == temp_ejemplo.Nombre_Programa).first()
            print(f"Programa '{temp_ejemplo.Nombre_Programa}' encontrado: {programa_match is not None}")
            if programa_match:
                print(f"  ID Programa: {programa_match.Id_Programa}")
        
        print(f"=================================")
        
        # **NUEVO: Contar registros en Matricula ANTES del SP**
        print(f"\n=== CONTEO ANTES DEL SP ===")
        count_antes = db.query(Matricula).count()
        print(f"Total registros en Matricula ANTES: {count_antes}")
        
        print(f"\n=== PARÁMETROS DEL SP ===")
        print(f"@UUnidad_Academica = '{unidad_sigla}' (tipo: {type(unidad_sigla).__name__})")
        print(f"@SSalones = '{total_grupos}' (tipo: {type(total_grupos).__name__})")
        print(f"@UUsuario = '{sess.id_usuario}' (tipo: {type(usuario_sp).__name__})")
        print(f"@PPeriodo = '{periodo}' (tipo: {type(periodo).__name__})")
        print(f"@HHost = '{host_sp}' (tipo: {type(host_sp).__name__})")
        print(f"@NNivel = '{nivel}' (tipo: {type(nivel).__name__})")
        print(f"========================")
                    
        # Ejecutar el stored procedure (centralizado en el servicio)
        try:
            execute_sp_actualiza_matricula_por_unidad_academica(
                db,
                unidad_sigla=unidad_sigla,
                salones=total_grupos,
                usuario=usuario_sp,
                periodo=periodo,
                host=host_sp,
                nivel=nivel,
            )
            print("SP ejecutado exitosamente")
            
            # **NUEVO: Contar registros en Matricula DESPUÉS del SP**
            print(f"\n=== CONTEO DESPUÉS DEL SP ===")
            count_despues = db.query(Matricula).count()
            print(f"Total registros en Matricula DESPUÉS: {count_despues}")
            print(f"Diferencia: {count_despues - count_antes} registros")
            
            if count_despues == count_antes:
                print(f"⚠️ WARNING: El SP no insertó ni actualizó registros en Matricula")
                print(f"⚠️ Posibles causas:")
                print(f"   1. No había datos en Temp_Matricula para procesar")
                print(f"   2. Los datos en Temp_Matricula no coinciden con catálogos")
                print(f"   3. El SP tiene un problema interno")
            elif count_despues > count_antes:
                print(f"✅ El SP insertó {count_despues - count_antes} registros nuevos")
            else:
                print(f"⚠️ El SP eliminó {count_antes - count_despues} registros (esto no debería pasar)")
            
            # LIMPIAR VALIDACIONES PREVIAS cuando el capturista hace cambios
            # Esto permite que los validadores vuelvan a validar/rechazar
            print(f"\n🔄 Limpiando validaciones previas del periodo...")
            id_unidad_academica = int(sess.id_unidad_academica)
            
            # Obtener el ID del periodo
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()
            if periodo_obj:
                periodo_id = periodo_obj.Id_Periodo
                
                # Eliminar registros de validación anteriores para este periodo/formato
                validaciones_eliminadas = db.query(Validacion).filter(
                    Validacion.Id_Periodo == periodo_id,
                    Validacion.Id_Formato == 1  # Formato de matrícula
                ).delete()
                
                db.commit()
                print(f"✅ {validaciones_eliminadas} validaciones previas eliminadas")
                print(f"   Los validadores pueden volver a validar/rechazar")
            else:
                print(f"⚠️  No se pudo obtener ID del periodo para limpiar validaciones")
                
        except Exception as sp_error:
            print(f"ERROR al ejecutar SP: {sp_error}")
            raise
        
        # Verificar que Temp_Matricula quedó vacía (el SP hace TRUNCATE)
        temp_count_after = db.query(Temp_Matricula).count()
        
        print(f"Registros en Temp_Matricula después: {temp_count_after}")
        print("=== ACTUALIZACIÓN COMPLETADA ===")
        
        return {
            "mensaje": "Matrícula actualizada exitosamente",
            "registros_procesados": temp_count,
            "temp_matricula_limpiada": temp_count_after == 0,
            "usuario": usuario_sp,
            "periodo": periodo,
            "timestamp": datetime.now().isoformat(),
            # **NUEVO: Información de diagnóstico**
            "diagnostico": {
                "registros_antes": count_antes,
                "registros_despues": count_despues,
                "diferencia": count_despues - count_antes,
                "sp_hizo_cambios": count_despues != count_antes
            }
        }
        
    except Exception as e:
        db.rollback()
        print(f"ERROR al actualizar matrícula: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al actualizar la matrícula: {str(e)}")

@router.get("/diagnostico_sp")
async def diagnostico_sp(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint de diagnóstico para analizar por qué no se actualiza la matrícula.
    Simula los JOINs del SP sin hacer cambios.
    """
    try:
        print(f"\n{'='*60}")
        print(f"DIAGNÓSTICO DETALLADO DEL SP")
        print(f"{'='*60}")
        
        # Contar registros en las tablas principales
        temp_count = db.query(Temp_Matricula).count()
        matricula_count = db.query(Matricula).count()
        
        print(f"Registros en Temp_Matricula: {temp_count}")
        print(f"Registros en Matricula: {matricula_count}")
        
        if temp_count == 0:
            return {"error": "No hay datos en Temp_Matricula para diagnosticar"}
        
        # Obtener todos los registros de Temp_Matricula
        temp_records = db.query(Temp_Matricula).all()
        
        diagnostico_resultados = []
        
        for i, tmp in enumerate(temp_records, 1):
            print(f"\n--- DIAGNÓSTICO REGISTRO {i} ---")
            print(f"Temp_Matricula record: {tmp.Periodo}, {tmp.Sigla}, {tmp.Nombre_Programa}")
            
            resultado = {
                'registro': i,
                'temp_data': {
                    'Periodo': tmp.Periodo,
                    'Sigla': tmp.Sigla,
                    'Nombre_Programa': tmp.Nombre_Programa,
                    'Nombre_Rama': tmp.Nombre_Rama,
                    'Nivel': tmp.Nivel,
                    'Modalidad': tmp.Modalidad,
                    'Turno': tmp.Turno,
                    'Semestre': tmp.Semestre,
                    'Grupo_Edad': tmp.Grupo_Edad,
                    'Tipo_Ingreso': tmp.Tipo_Ingreso,
                    'Sexo': tmp.Sexo,
                    'Matricula': tmp.Matricula
                },
                'joins_encontrados': {},
                'joins_faltantes': [],
                'posibles_coincidencias': 0
            }
            
            # Verificar cada JOIN del SP
            
            # 1. Cat_Periodo
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == tmp.Periodo).first()
            if periodo_obj:
                resultado['joins_encontrados']['Cat_Periodo'] = {
                    'id': periodo_obj.Id_Periodo,
                    'valor': periodo_obj.Periodo
                }
                print(f"✅ Periodo encontrado: ID={periodo_obj.Id_Periodo}")
            else:
                resultado['joins_faltantes'].append('Cat_Periodo')
                print(f"❌ Periodo '{tmp.Periodo}' NO encontrado")
            
            # 2. Cat_Unidad_Academica
            unidad_obj = db.query(Unidad_Academica).filter(Unidad_Academica.Sigla == tmp.Sigla).first()
            if unidad_obj:
                resultado['joins_encontrados']['Cat_Unidad_Academica'] = {
                    'id': unidad_obj.Id_Unidad_Academica,
                    'valor': unidad_obj.Sigla
                }
                print(f"✅ Unidad encontrada: ID={unidad_obj.Id_Unidad_Academica}")
            else:
                resultado['joins_faltantes'].append('Cat_Unidad_Academica')
                print(f"❌ Unidad '{tmp.Sigla}' NO encontrada")
            
            # 3. Cat_Programas
            programa_obj = db.query(Programas).filter(Programas.Nombre_Programa == tmp.Nombre_Programa).first()
            if programa_obj:
                resultado['joins_encontrados']['Cat_Programas'] = {
                    'id': programa_obj.Id_Programa,
                    'valor': programa_obj.Nombre_Programa
                }
                print(f"✅ Programa encontrado: ID={programa_obj.Id_Programa}")
            else:
                resultado['joins_faltantes'].append('Cat_Programas')
                print(f"❌ Programa '{tmp.Nombre_Programa}' NO encontrado")
            
            # Continuar con el resto de JOINs...
            # 4. Cat_Rama
            rama_obj = db.query(Rama).filter(Rama.Nombre_Rama == tmp.Nombre_Rama).first()
            if rama_obj:
                resultado['joins_encontrados']['Cat_Rama'] = {
                    'id': rama_obj.Id_Rama,
                    'valor': rama_obj.Nombre_Rama
                }
                print(f"✅ Rama encontrada: ID={rama_obj.Id_Rama}")
            else:
                resultado['joins_faltantes'].append('Cat_Rama')
                print(f"❌ Rama '{tmp.Nombre_Rama}' NO encontrada")
            
            # Si todos los JOINs principales son exitosos, buscar coincidencias en Matricula
            if all(key in resultado['joins_encontrados'] for key in ['Cat_Periodo', 'Cat_Unidad_Academica', 'Cat_Programas', 'Cat_Rama']):
                # Simular la condición WHERE del SP
                matricula_matches = db.query(Matricula).filter(
                    Matricula.Id_Periodo == resultado['joins_encontrados']['Cat_Periodo']['id'],
                    Matricula.Id_Unidad_Academica == resultado['joins_encontrados']['Cat_Unidad_Academica']['id'],
                    Matricula.Id_Programa == resultado['joins_encontrados']['Cat_Programas']['id'],
                    Matricula.Id_Rama == resultado['joins_encontrados']['Cat_Rama']['id']
                ).count()
                
                resultado['posibles_coincidencias'] = matricula_matches
                print(f"🎯 Coincidencias potenciales en Matricula: {matricula_matches}")
            
            diagnostico_resultados.append(resultado)
        
        print(f"{'='*60}")
        
        return {
            "total_temp_records": temp_count,
            "total_matricula_records": matricula_count,
            "diagnostico_por_registro": diagnostico_resultados,
            "resumen": {
                "registros_con_todos_joins": len([r for r in diagnostico_resultados if not r['joins_faltantes']]),
                "registros_con_coincidencias": len([r for r in diagnostico_resultados if r['posibles_coincidencias'] > 0])
            }
        }
        
    except Exception as e:
        print(f"ERROR en diagnóstico: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@router.post("/limpiar_temp_matricula")
async def limpiar_temp_matricula(db: Session = Depends(get_db)):
    """
    Endpoint temporal para limpiar la tabla Temp_Matricula.
    Útil para testing cuando hay datos con formato incorrecto.
    """
    try:
        count_before = db.query(Temp_Matricula).count()
        db.query(Temp_Matricula).delete()
        db.commit()
        
        return {
            "mensaje": f"Tabla Temp_Matricula limpiada exitosamente",
            "registros_eliminados": count_before
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Error al limpiar Temp_Matricula: {str(e)}"}


@router.post("/preparar_turno")
async def preparar_turno(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para VALIDAR un turno individual (Fase 1 del nuevo sistema).
    Este endpoint:
    1. Ejecuta SP_Actualiza_Matricula_Por_Unidad_Academica (igual que Guardar Avance)
    2. NO actualiza el semáforo del semestre
    3. Marca el turno como validado para bloqueo permanente
    4. Retorna success=True para que el frontend bloquee los inputs
    
    El SP_Actualiza_Matricula_Por_Semestre_AU se ejecutará automáticamente
    cuando todos los turnos del semestre estén validados.
    """
    try:
        # Obtener datos del request
        data = await request.json()
        
        # Parámetros necesarios
        periodo = data.get('periodo')
        programa = data.get('programa')
        modalidad = data.get('modalidad')
        semestre = data.get('semestre')
        turno = data.get('turno')
        
        # Obtener datos del usuario desde cookies
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario

        # Login del usuario (el SPs esperan el login, no el nombre completo)
        usuario_login = sess.usuario or request.cookies.get("Usuario", "")
        # Mantener nombre completo solo para mensajes
        nombre_completo = f"{nombre_usuario} {apellidoP_usuario} {apellidoM_usuario}".strip()
        usuario_sp = usuario_login or 'sistema'
        
        # Obtener host
        host_sp = get_request_host(request)
        
        print(f"\n{'='*60}")
        print(f"VALIDANDO TURNO INDIVIDUAL - SP POR UNIDAD ACADÉMICA")
        print(f"{'='*60}")
        print(f"Periodo (input): {periodo}")
        print(f"Programa ID: {programa}")
        print(f"Modalidad ID: {modalidad}")
        print(f"Semestre ID: {semestre}")
        print(f"Turno ID: {turno}")
        print(f"Usuario (login): {usuario_sp}")
        print(f"Host: {host_sp}")
        
        # Validar parámetros obligatorios
        if not all([periodo, programa, modalidad, semestre, turno]):
            return {
                "error": "Faltan parámetros obligatorios",
                "detalles": {
                    "periodo": periodo,
                    "programa": programa,
                    "modalidad": modalidad,
                    "semestre": semestre,
                    "turno": turno
                }
            }
        
        # Convertir período a literal si viene como ID
        if str(periodo).isdigit():
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo)).first()
            if periodo_obj:
                periodo_literal = periodo_obj.Periodo
                print(f"🔄 Período convertido de ID {periodo} → '{periodo_literal}'")
            else:
                _, periodo_literal = get_ultimo_periodo(db)
                if not periodo_literal:
                    return {"error": "No se pudo obtener un periodo válido"}
                print(f"⚠️ ID de período no encontrado, usando último periodo: '{periodo_literal}'")
        else:
            periodo_literal = str(periodo)
            print(f"✅ Período en literal: '{periodo_literal}'")
        
        # Obtener nombres literales desde la BD para el SP
        unidad = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        unidad_sigla = unidad.Sigla if unidad else ''
        
        nivel_obj = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        nivel_nombre = nivel_obj.Nivel if nivel_obj else ''
        
        semestre_obj = db.query(Semestre).filter(Semestre.Id_Semestre == int(semestre)).first()
        semestre_nombre = semestre_obj.Semestre if semestre_obj else f"Semestre {semestre}"
        
        turno_obj = db.query(Turno).filter(Turno.Id_Turno == int(turno)).first()
        turno_nombre = turno_obj.Turno if turno_obj else f"Turno {turno}"
        
        print(f"\n📋 Turno validado - datos guardados en Temp_Matricula")
        print(f"   Unidad: {unidad_sigla}")
        print(f"   Nivel: {nivel_nombre}")
        print(f"   Período: {periodo_literal}")
        print(f"   ⚠️  SP_Actualiza_Matricula_Por_Unidad_Academica NO se ejecuta aquí (solo preparar_turno)")
        
        print(f"\n✅ Turno preparado exitosamente (datos permanecen en Temp_Matricula)")
        print(f"📋 Semestre: {semestre_nombre}")
        print(f"🕐 Turno: {turno_nombre}")
        print(f"⏭️  El SP_Actualiza_Matricula_Por_Semestre_AU se ejecutará cuando todos los turnos estén validados")
        
        # Retornar éxito
        return {
            "success": True,
            "mensaje": f"Turno {turno_nombre} del {semestre_nombre} preparado exitosamente. Datos guardados en Temp_Matricula.",
            "turno_validado": turno_nombre,
            "semestre": semestre_nombre,
            "fase": "turno_individual",
            "sp_ejecutado": "ninguno (datos en Temp_Matricula)",
            "nota": "El turno está bloqueado. El SP final se ejecutará cuando todos los turnos estén completos"
        }
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR al validar turno: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": f"Error al validar el turno: {str(e)}",
            "success": False
        }


@router.post("/validar_captura_semestre")
async def validar_captura_semestre(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para validar y finalizar TODOS LOS TURNOS de un semestre (Fase 2 - SP FINAL).
    Este endpoint:
    1. Ejecuta el SP SP_Actualiza_Matricula_Por_Semestre_AU
    2. Actualiza el semáforo del semestre a "Completado" (ID=3)
    3. Registra la acción en bitácora
    4. Devuelve los datos actualizados
    
    SOLO debe llamarse cuando todos los turnos del semestre estén validados.
    """
    try:
        # Obtener datos del request
        data = await request.json()
        
        # Parámetros necesarios
        periodo = data.get('periodo')
        programa = data.get('programa')
        modalidad = data.get('modalidad')
        semestre = data.get('semestre')
        
        # Obtener datos del usuario desde cookies
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        
        # Construir nombre completo del usuario
        nombre_completo = f"{nombre_usuario} {apellidoP_usuario} {apellidoM_usuario}".strip()
        usuario_sp = nombre_completo or 'sistema'
        
        # Obtener host
        host_sp = get_request_host(request)
        
        print(f"\n{'='*60}")
        print(f"EJECUTANDO SP FINAL - CONSOLIDACIÓN DEL SEMESTRE COMPLETO")
        print(f"{'='*60}")
        print(f"⚠️  TODOS LOS TURNOS DEL SEMESTRE DEBEN ESTAR VALIDADOS")
        print(f"Periodo (input): {periodo}")
        print(f"Programa ID: {programa}")
        print(f"Modalidad ID: {modalidad}")
        print(f"Semestre ID: {semestre}")
        print(f"Usuario: {usuario_sp}")
        print(f"Host: {host_sp}")
        
        # Validar parámetros obligatorios (sin turno)
        if not all([periodo, programa, modalidad, semestre]):
            return {
                "error": "Faltan parámetros obligatorios",
                "detalles": {
                    "periodo": periodo,
                    "programa": programa,
                    "modalidad": modalidad,
                    "semestre": semestre
                }
            }

        # Convertir período a literal si viene como ID (el SP requiere literal ej: '2025-2026/1')
        if str(periodo).isdigit():
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo)).first()
            if periodo_obj:
                periodo_literal = periodo_obj.Periodo
                print(f"🔄 Período convertido de ID {periodo} → '{periodo_literal}'")
            else:
                _, periodo_literal = get_ultimo_periodo(db)
                if not periodo_literal:
                    return {"error": "No se pudo obtener un periodo válido"}
                print(f"⚠️ ID de período no encontrado, usando último periodo: '{periodo_literal}'")
        else:
            periodo_literal = str(periodo)
            print(f"✅ Período en literal: '{periodo_literal}'")
        
        # Obtener nombres literales desde la BD para el SP
        # Unidad Académica
        unidad = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        unidad_sigla = unidad.Sigla if unidad else ''
        
        # Programa
        programa_obj = db.query(Programas).filter(
            Programas.Id_Programa == int(programa)
        ).first()
        programa_nombre = programa_obj.Nombre_Programa if programa_obj else ''
        
        # Modalidad
        modalidad_obj = db.query(Modalidad).filter(
            Modalidad.Id_Modalidad == int(modalidad)
        ).first()
        modalidad_nombre = modalidad_obj.Modalidad if modalidad_obj else ''
        
        # Semestre
        semestre_obj = db.query(Semestre).filter(
            Semestre.Id_Semestre == int(semestre)
        ).first()
        semestre_nombre = semestre_obj.Semestre if semestre_obj else ''
        
        # Nivel
        nivel_obj = db.query(Nivel).filter(
            Nivel.Id_Nivel == id_nivel
        ).first()
        nivel_nombre = nivel_obj.Nivel if nivel_obj else ''
        
        print(f"\n📋 Valores literales para el SP:")
        print(f"Unidad Académica: {unidad_sigla}")
        print(f"Programa: {programa_nombre}")
        print(f"Modalidad: {modalidad_nombre}")
        print(f"Semestre: {semestre_nombre}")
        print(f"Nivel: {nivel_nombre}")
        print(f"Período (literal): {periodo_literal}")
        
        # Validar que se obtuvieron todos los valores
        if not all([unidad_sigla, programa_nombre, modalidad_nombre, semestre_nombre, nivel_nombre]):
            return {
                "error": "No se pudieron obtener los nombres literales de los catálogos",
                "detalles": {
                    "unidad": unidad_sigla,
                    "programa": programa_nombre,
                    "modalidad": modalidad_nombre,
                    "semestre": semestre_nombre,
                    "nivel": nivel_nombre
                }
            }
        
        # Ejecutar el SP SP_Actualiza_Matricula_Por_Semestre_AU
        # Nota: El SP requiere @SSalones, lo obtenemos del request (Total Grupos)
        total_grupos = int(data.get('total_grupos', 0) or 0)
        print(f"Total de Grupos (salones) para validación: {total_grupos}")
        
        # Ejecutar SP de validación por semestre
        rows_list = execute_sp_actualiza_matricula_por_semestre_au(
            db,
            unidad_sigla=unidad_sigla,
            programa_nombre=programa_nombre,
            modalidad_nombre=modalidad_nombre,
            semestre_nombre=semestre_nombre,
            salones=total_grupos,
            usuario=usuario_sp,
            periodo=periodo_literal,
            host=host_sp,
            nivel=nivel_nombre,
        )
        
        print(f"\n✅ SP_Actualiza_Matricula_Por_Semestre_AU ejecutado exitosamente")
        print(f"Filas finales devueltas: {len(rows_list)}")
        
        # VERIFICAR SI SE DEBE EJECUTAR SP_Finaliza_Captura_Matricula
        print(f"\n{'='*60}")
        print(f"🔍 VERIFICANDO CONDICIONES PARA SP_Finaliza_Captura_Matricula")
        print(f"{'='*60}")
        
        # Obtener el período como ID para consultar SemaforoUnidadAcademica
        if str(periodo).isdigit():
            periodo_id = int(periodo)
        else:
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo_literal).first()
            if periodo_obj:
                periodo_id = periodo_obj.Id_Periodo
            else:
                periodo_id, _ = get_ultimo_periodo(db)
                if not periodo_id:
                    periodo_id = 1  # Fallback solo si no hay periodos
        
        # Verificar el estado del semáforo general en SemaforoUnidadAcademica
        semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
            SemaforoUnidadAcademica.Id_Periodo == periodo_id,
            SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
            SemaforoUnidadAcademica.Id_Formato == 1,  # Formato de matrícula
            SemaforoUnidadAcademica.Id_Nivel == id_nivel
        ).first()
        
        if not semaforo_unidad:
            print(f"⚠️  No se encontró registro en SemaforoUnidadAcademica")
            print(f"   Periodo: {periodo_id}, Unidad: {id_unidad_academica}, Formato: 1")
            debe_ejecutar_sp_final = False
        elif semaforo_unidad.Id_Semaforo == 3:
            print(f"⏭️  SemaforoUnidadAcademica ya está en estado 3 (COMPLETADO)")
            print(f"   SP_Finaliza_Captura_Matricula ya fue ejecutado previamente")
            debe_ejecutar_sp_final = False
        elif semaforo_unidad.Id_Semaforo == 2:
            print(f"✅ SemaforoUnidadAcademica está en estado 2 (CAPTURA)")
            print(f"🔍 Verificando que TODOS los semestres de TODAS las combinaciones Programa-Modalidad estén en estado 3...")

            # NUEVO: Verificar en tabla Semaforo_Semestre_Unidad_Academica por UA+Periodo+Formato=1
            # FILTRANDO SOLO las combinaciones PM cuyo programa pertenece al nivel actual
            from backend.database.models.SemaforoSemestreUnidadAcademica import SemaforoSemestreUnidadAcademica
            from backend.database.models.ProgramaModalidad import ProgramaModalidad

            registros_semaforo = (
                db.query(SemaforoSemestreUnidadAcademica)
                .join(ProgramaModalidad, ProgramaModalidad.Id_Modalidad_Programa == SemaforoSemestreUnidadAcademica.Id_Modalidad_Programa)
                .join(Programas, Programas.Id_Programa == ProgramaModalidad.Id_Programa)
                .filter(
                    SemaforoSemestreUnidadAcademica.Id_Periodo == periodo_id,
                    SemaforoSemestreUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                    SemaforoSemestreUnidadAcademica.Id_Formato == 1,
                    Programas.Id_Nivel == id_nivel
                )
                .all()
            )

            total_registros = len(registros_semaforo)
            total_en_3 = sum(1 for r in registros_semaforo if r.Id_Semaforo == 3)

            print(f"   📊 Registros Semaforo_Semestre_UA (PM de nivel actual): {total_registros}")
            print(f"   ✅ Registros en estado 3: {total_en_3}")

            # Mostrar desglose por Id_Modalidad_Programa
            pm_map = {}
            for r in registros_semaforo:
                pm_map.setdefault(r.Id_Modalidad_Programa, []).append(r)
            for pm_id, lista in pm_map.items():
                en3 = sum(1 for x in lista if x.Id_Semaforo == 3)
                print(f"      • PM {pm_id}: {en3}/{len(lista)} semestres en 3")

            if total_registros > 0 and total_en_3 == total_registros:
                print(f"\n✅ CONDICIONES GLOBALES CUMPLIDAS: TODOS los semestres de TODAS las PM están en 3")
                debe_ejecutar_sp_final = True
            else:
                faltantes = total_registros - total_en_3
                print(f"\n⏭️  NO se ejecutará SP_Finaliza_Captura_Matricula: Faltan {faltantes} semestres por completar en 3 (global)")
                debe_ejecutar_sp_final = False
        else:
            print(f"⚠️  SemaforoUnidadAcademica en estado desconocido: {semaforo_unidad.Id_Semaforo}")
            debe_ejecutar_sp_final = False
        
        # Ejecutar SP_Finaliza_Captura_Matricula solo si se cumplen las condiciones
        sp_final_ejecutado = False
        if debe_ejecutar_sp_final:
            print(f"\n{'='*60}")
            print(f"🚀 EJECUTANDO SP_Finaliza_Captura_Matricula")
            print(f"{'='*60}")
            
            execute_sp_finaliza_captura_matricula(
                db,
                unidad_sigla=unidad_sigla,
                programa_nombre=programa_nombre,
                modalidad_nombre=modalidad_nombre,
                semestre_nombre=semestre_nombre,
                salones=total_grupos,
                usuario=usuario_sp,
                periodo=periodo_literal,
                host=host_sp,
                nivel=nivel_nombre,
            )
            
            print(f"✅ SP_Finaliza_Captura_Matricula ejecutado exitosamente")
            # Verificación inmediata en BD: Semaforo_Unidad_Academica para el NIVEL actual
            try:
                from sqlalchemy import text as _sql_text
                res = db.execute(_sql_text(
                    """
                    SELECT Id_Periodo, Id_Unidad_Academica, 
                           CASE WHEN COL_LENGTH('Semaforo_Unidad_Academica','Id_Nivel') IS NOT NULL THEN Id_Nivel ELSE NULL END AS Id_Nivel,
                           Id_Formato, Id_Semaforo, Fecha_Final
                    FROM Semaforo_Unidad_Academica
                    WHERE Id_Periodo = :p AND Id_Unidad_Academica = :ua AND Id_Formato = 1
                    """
                ), {'p': periodo_id, 'ua': id_unidad_academica}).fetchall()
                print("   Registros Semaforo_UA tras SP:")
                for row in res:
                    print(f"     • Nivel={row[2]}  Estado={row[4]}  Fecha_Final={row[5]}")
            except Exception as _e:
                print(f"   Aviso: No se pudo verificar Semaforo_UA post-SP: {_e}")
            sp_final_ejecutado = True
        else:
            print(f"\n⏭️  SP_Finaliza_Captura_Matricula NO ejecutado (condiciones no cumplidas)")
        
        # Verificar semáforo sin SQL crudo: reconsultar SP y extraer estado
        print(f"\n🔍 Consultando estado actualizado del semáforo vía SP...")
        estado_semaforo_actualizado = get_estado_semaforo_desde_sp(
            db,
            id_unidad_academica=id_unidad_academica,
            id_nivel=id_nivel,
            periodo_input=periodo_literal,
            usuario=usuario_sp,
            host=host_sp,
            programa_nombre=programa_nombre,
            modalidad_nombre=modalidad_nombre,
            semestre_nombre=semestre_nombre,
        )
        
        # Construir lista de SPs ejecutados
        sps_ejecutados = ["SP_Actualiza_Matricula_Por_Semestre_AU"]
        if sp_final_ejecutado:
            sps_ejecutados.append("SP_Finaliza_Captura_Matricula")
        
        # Mensaje apropiado según si se ejecutó el SP final
        if sp_final_ejecutado:
            mensaje = f"Semestre {semestre_nombre} consolidado. ¡TODA LA CAPTURA FINALIZADA!"
        else:
            mensaje = f"Semestre {semestre_nombre} consolidado (aún faltan semestres por completar)"
        
        return {
            "success": True,
            "mensaje": mensaje,
            "rows": rows_list,
            "semestre_validado": semestre_nombre,
            "estado_semaforo": estado_semaforo_actualizado,
            "sp_final_ejecutado": sp_final_ejecutado,
            "fase": "sp_final_consolidado" if sp_final_ejecutado else "sp_semestre_actualizado",
            "debug": {
                "sp_ejecutados": sps_ejecutados,
                "parametros": {
                    "unidad": unidad_sigla,
                    "programa": programa_nombre,
                    "modalidad": modalidad_nombre,
                    "semestre": semestre_nombre,
                    "salones": total_grupos,
                    "usuario": usuario_sp,
                    "periodo": periodo_literal,
                    "host": host_sp,
                    "nivel": nivel_nombre
                }
            }
        }
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR al validar captura: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": f"Error al validar la captura del semestre: {str(e)}",
            "success": False
        }


@router.post("/validar_semestre_rol")
async def validar_semestre_rol(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para que roles de validación (ID 4, 5, 6, 7, 8) aprueben la matrícula completa.
    Ejecuta SP_Valida_Matricula para marcar como validada.
    """
    try:
        # Obtener datos del usuario desde cookies
        usuario = sess.usuario  # Login del usuario
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        id_usuario = int(sess.id_usuario)
        id_rol = int(sess.id_rol)
        id_unidad_academica = int(sess.id_unidad_academica)
        # Asegurar lectura de nivel ANTES de cualquier uso/log
        try:
            id_nivel = int(sess.id_nivel)
        except Exception:
            id_nivel = 0
        
        # Construir nombre completo para mostrar
        nombre_completo = f"{nombre_usuario} {apellidoP_usuario} {apellidoM_usuario}".strip()
        
        # IMPORTANTE: El SP espera el LOGIN del usuario en @UUsuario
        usuario_sp = usuario or 'sistema'
        
        # Validar que sea un rol de validación
        if id_rol not in [4, 5, 6, 7, 8, 9]:
            return {
                "success": False,
                "error": "Solo los roles de validación pueden usar esta función"
            }
        
        # Obtener datos del request
        body = await request.json()
        periodo_id = body.get("periodo")
        
        # Obtener host
        host_sp = get_request_host(request)
        
        print(f"\n{'='*60}")
        print(f"✅ VALIDACIÓN DE MATRÍCULA - ROL {id_rol}")
        print(f"{'='*60}")
        print(f"Usuario: {usuario_sp}")
        print(f"Periodo ID: {periodo_id}")
        print(f"Unidad Académica ID: {id_unidad_academica}")
        print(f"Host: {host_sp}")
        
        # Convertir período a literal si viene como ID
        if str(periodo_id).isdigit():
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_id)).first()
            if periodo_obj:
                periodo_literal = periodo_obj.Periodo
                print(f"🔄 Período convertido de ID {periodo_id} → '{periodo_literal}'")
            else:
                _, periodo_literal = get_ultimo_periodo(db)
                if not periodo_literal:
                    return {"success": False, "error": "No se pudo obtener un periodo válido"}
                print(f"⚠️ ID de período no encontrado, usando último periodo: '{periodo_literal}'")
        else:
            periodo_literal = str(periodo_id)
            print(f"✅ Período en literal: '{periodo_literal}'")
        
        # Obtener sigla de la unidad académica
        unidad = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        unidad_sigla = unidad.Sigla if unidad else ''
        
        if not unidad_sigla:
            return {
                "success": False,
                "error": "No se pudo obtener la Unidad Académica"
            }
        
        print(f"📋 Unidad Académica: {unidad_sigla}")
        
        # EJECUTAR SP_Valida_Matricula
        print(f"\n🚀 Ejecutando SP_Valida_Matricula...")
        print(f"   @PPeriodo = '{periodo_literal}'")
        print(f"   @UUnidad_Academica = '{unidad_sigla}'")
        print(f"   @UUsuario = '{usuario_sp}' (LOGIN del usuario)")
        print(f"   @HHost = '{host_sp}'")
        #print(f"   @semaforo = 3")
        print(f"   @NNivel (Id) = {id_nivel}")
        # Estado previo del semáforo
        try:
            # Obtener el periodo_id dinámicamente
            periodo_id_validar, _ = get_ultimo_periodo(db)
            if not periodo_id_validar:
                periodo_id_validar = 1  # Fallback
            
            semaforo_prev = db.query(SemaforoUnidadAcademica).filter(
                SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoUnidadAcademica.Id_Periodo == periodo_id_validar,
                SemaforoUnidadAcademica.Id_Formato == 1,
                SemaforoUnidadAcademica.Id_Nivel == id_nivel
            ).first()
            print(f"🔎 Semáforo antes de validar: {semaforo_prev.Id_Semaforo if semaforo_prev else 'N/A'}")
        except Exception as _e_prev:
            print(f"ℹ️ No se pudo leer semáforo previo: {_e_prev}")
        
        execute_sp_valida_matricula(
            db,
            periodo=periodo_literal,
            unidad_sigla=unidad_sigla,
            usuario=usuario_sp,
            host=host_sp,
           # semaforo=3,  # Estado validado
            nivel=id_nivel,
            nota=f"Validado por {nombre_completo}"
        )
        # Diagnóstico: Mostrar filas de Semaforo_UA para esta UA+Periodo con y sin Id_Nivel
        try:
            from sqlalchemy import text as _sql_text
            diag_rows = db.execute(_sql_text(
                """
                SELECT sua.Id_Unidad_Academica, sua.Id_Periodo, sua.Id_Formato,
                       CASE WHEN COL_LENGTH('Semaforo_Unidad_Academica','Id_Nivel') IS NOT NULL THEN sua.Id_Nivel ELSE NULL END AS Id_Nivel,
                       sua.Id_Semaforo, sua.Fecha_Modificacion
                FROM [SAE].[dbo].[Semaforo_Unidad_Academica] sua
                WHERE sua.Id_Unidad_Academica = :ua AND sua.Id_Periodo = (SELECT Id_Periodo FROM [SAE].[dbo].[Cat_Periodo] WHERE Periodo = :p) AND sua.Id_Formato = 1
                """
            ), {'ua': id_unidad_academica, 'p': periodo_literal}).fetchall()
            print("📊 Semaforo_UA registros para UA+Periodo (formato=1):")
            for r in diag_rows:
                print(f"   • Id_Nivel={r[3]}  Id_Semaforo={r[4]}  Fecha={r[5]}")
        except Exception as _e_diag:
            print(f"ℹ️ No se pudo ejecutar diagnóstico de Semaforo_UA: {_e_diag}")
        # Releer semáforo después del SP
        try:
            # Obtener el periodo_id dinámicamente
            periodo_id_post, _ = get_ultimo_periodo(db)
            if not periodo_id_post:
                periodo_id_post = 1  # Fallback
            
            semaforo_post = db.query(SemaforoUnidadAcademica).filter(
                SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoUnidadAcademica.Id_Periodo == periodo_id_post,
                SemaforoUnidadAcademica.Id_Formato == 1,
                SemaforoUnidadAcademica.Id_Nivel == id_nivel
            ).first()
            print(f"🔎 Semáforo después de validar: {semaforo_post.Id_Semaforo if semaforo_post else 'N/A'}")
        except Exception as _e_post:
            print(f"ℹ️ No se pudo leer semáforo posterior: {_e_post}")

        print(f"✅ Matrícula validada exitosamente")
        
        return {
            "success": True,
            "mensaje": f"Matrícula validada exitosamente",
            "data": {
                "validado_por": nombre_completo,
                "usuario_login": usuario_sp,
                "id_usuario": id_usuario,
                "id_rol": id_rol,
                "fecha_validacion": datetime.now().isoformat(),
                "periodo": periodo_literal,
                "unidad_academica": unidad_sigla
            }
        }
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR al validar matrícula: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": f"Error al validar la matrícula: {str(e)}"
        }


@router.post("/ejecutar_sp_finalizar_captura")
async def ejecutar_sp_finalizar_captura(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para ejecutar SP_Finaliza_Captura_Matricula después de validar todos los semestres.
    Verifica que TODOS los semestres de TODAS las combinaciones Programa-Modalidad
    de la UA y periodo estén en semáforo 3 (Id_Formato=1).
    """
    try:
        # Obtener datos del request
        body = await request.json()
        periodo = body.get('periodo')
        # Ya no se requiere filtrar por programa/modalidad para final global
        
        # Obtener datos del usuario desde cookies
        id_unidad_academica = int(sess.id_unidad_academica)
        id_nivel = int(sess.id_nivel)
        usuario = sess.usuario
        host = request.headers.get("host", "localhost")

        print(f"\n{'='*60}")
        print(f"🚀 EJECUTAR SP_Finaliza_Captura_Matricula")
        print(f"{'='*60}")
        print(f"   Periodo: {periodo}")
        print(f"   Unidad: {id_unidad_academica}")
        print(f"   Nivel: {id_nivel}")
        print(f"   Finalización GLOBAL por UA+Periodo (todas PM)")
        
        # Obtener periodo como ID
        if str(periodo).isdigit():
            periodo_id = int(periodo)
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == periodo_id).first()
            periodo_literal = periodo_obj.Periodo if periodo_obj else str(periodo)
        else:
            periodo_literal = periodo
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo_literal).first()
            if periodo_obj:
                periodo_id = periodo_obj.Id_Periodo
            else:
                periodo_id, _ = get_ultimo_periodo(db)
                if not periodo_id:
                    periodo_id = 1  # Fallback solo si no hay periodos
        
        # Consultar SOLO los semestres de esta UA, Periodo, Formato
        # cuyo Programa pertenece al nivel actual, uniendo PM y Programas
        from backend.database.models.ProgramaModalidad import ProgramaModalidad
        semaforos_semestres = (
            db.query(SemaforoSemestreUnidadAcademica)
            .join(ProgramaModalidad, ProgramaModalidad.Id_Modalidad_Programa == SemaforoSemestreUnidadAcademica.Id_Modalidad_Programa)
            .join(Programas, Programas.Id_Programa == ProgramaModalidad.Id_Programa)
            .filter(
                SemaforoSemestreUnidadAcademica.Id_Periodo == periodo_id,
                SemaforoSemestreUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoSemestreUnidadAcademica.Id_Formato == 1,
                Programas.Id_Nivel == id_nivel
            )
            .all()
        )
        
        if not semaforos_semestres or len(semaforos_semestres) == 0:
            return {
                "success": False,
                "error": f"No se encontraron semestres para esta combinación de UA, Periodo y Programa-Modalidad"
            }
        
        # Verificar que TODOS los semestres estén en estado 3
        total_semestres = len(semaforos_semestres)
        semestres_en_estado_3 = sum(1 for s in semaforos_semestres if s.Id_Semaforo == 3)
        
        print(f"\n📊 VERIFICACIÓN DE SEMESTRES:")
        print(f"   Total de semestres encontrados (nivel actual): {total_semestres}")
        print(f"   Semestres en estado 3: {semestres_en_estado_3}")
        
        # Mostrar detalle de cada semestre
        for sem in semaforos_semestres:
            estado_emoji = "✅" if sem.Id_Semaforo == 3 else "❌"
            print(f"   {estado_emoji} Semestre {sem.Id_Semestre}: Estado {sem.Id_Semaforo}")
        
        # Validar que TODOS estén en estado 3
        if semestres_en_estado_3 < total_semestres:
            semestres_faltantes = [s.Id_Semestre for s in semaforos_semestres if s.Id_Semaforo != 3]
            return {
                "success": False,
                "error": f"No todos los semestres están en estado 3. Faltan {total_semestres - semestres_en_estado_3} semestres. Semestres pendientes: {semestres_faltantes}"
            }
        
        print(f"\n✅ TODOS LOS SEMESTRES (GLOBAL) ESTÁN EN ESTADO 3 - Procediendo a ejecutar SP_Finaliza_Captura_Matricula...")
        
        # Obtener información necesaria para el SP
        unidad_obj = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        
        nivel_obj = db.query(Nivel).filter(Nivel.Id_Nivel == id_nivel).first()
        
        unidad_sigla = unidad_obj.Sigla if unidad_obj else ""
        nivel_nombre = getattr(nivel_obj, 'Nombre', None) or getattr(nivel_obj, 'Nivel', '')
        
        # Obtener datos desde el SP de consulta
        rows_sp, metadata_sp, debug_msg_sp, nota_rechazo_sp = execute_matricula_sp_with_context(
            db,
            id_unidad_academica,
            id_nivel,
            periodo_literal,
            periodo_literal,
            usuario,
            host,
        )
        
        # Obtener datos del primer registro para programa/modalidad/semestre
        if rows_sp and len(rows_sp) > 0:
            primer_row = rows_sp[0]
            programa_nombre = primer_row.get('Programa', '')
            modalidad_nombre = primer_row.get('Modalidad', '')
            semestre_nombre = primer_row.get('Semestre', '1')
            salones = primer_row.get('Total_Grupos', 0)
        else:
            return {"success": False, "error": "No se pudieron obtener datos para ejecutar el SP"}
        
        # Ejecutar SP_Finaliza_Captura_Matricula
        execute_sp_finaliza_captura_matricula(
            db,
            unidad_sigla=unidad_sigla,
            programa_nombre=programa_nombre,
            modalidad_nombre=modalidad_nombre,
            semestre_nombre=semestre_nombre,
            salones=salones,
            usuario=usuario,
            periodo=periodo_literal,
            host=host,
            nivel=nivel_nombre,
        )
        
        print(f"✅ SP_Finaliza_Captura_Matricula ejecutado exitosamente")
        
        return {
            "success": True,
            "mensaje": f"SP_Finaliza_Captura_Matricula ejecutado exitosamente. {total_semestres} semestres validados.",
            "sp_ejecutado": "SP_Finaliza_Captura_Matricula",
            "semestres_validados": total_semestres
        }
        
    except Exception as e:
        print(f"❌ Error al ejecutar SP_Finaliza_Captura_Matricula: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Error al ejecutar SP de finalización: {str(e)}"
        }


@router.post("/rechazar_semestre_rol")
async def rechazar_semestre_rol(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Endpoint para que roles de validación (ID 4, 5, 6, 7, 8) rechacen la matrícula.
    Ejecuta SP_Rechaza_Matricula y devuelve al capturista para correcciones.
    """
    try:
        # Obtener datos del usuario desde cookies
        print(f"\n🔍 DEBUG: Verificando cookies disponibles...")
        print(f"Todas las cookies: {list(request.cookies.keys())}")
        
        usuario = sess.usuario  # Login del usuario
        print(f"Cookie 'usuario': '{usuario}'")
        
        # Si no hay cookie 'usuario', intentar con otras variantes
        if not usuario:
            usuario = request.cookies.get("Usuario", "")  # Intento con mayúscula
            print(f"Cookie 'Usuario': '{usuario}'")
        
        if not usuario:
            usuario = request.cookies.get("username", "")  # Otro nombre posible
            print(f"Cookie 'username': '{usuario}'")
        
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        id_usuario = int(sess.id_usuario)
        id_rol = int(sess.id_rol)
        id_unidad_academica = int(sess.id_unidad_academica)
        
        print(f"Usuario extraído: '{usuario}'")
        print(f"Nombre: {nombre_usuario} {apellidoP_usuario} {apellidoM_usuario}")
        print(f"ID Usuario: {id_usuario}")
        print(f"ID Rol: {id_rol}")
        print(f"ID Nivel: {request.cookies.get('id_nivel', 'No disponible')}")
        
        # Construir nombre completo para el motivo
        nombre_completo = f"{nombre_usuario} {apellidoP_usuario} {apellidoM_usuario}".strip()
        
        # IMPORTANTE: El SP espera el LOGIN del usuario en @UUsuario, NO el nombre completo
        # El SP hace: select id_usuario from Usuarios where Usuario = @UUsuario
        usuario_sp = usuario if usuario else 'sistema'
        
        print(f"⚠️ Usuario final a usar en SP: '{usuario_sp}'")
        
        if usuario_sp == 'sistema':
            print(f"❌ ADVERTENCIA: No se encontró el login del usuario en las cookies!")
            print(f"   Esto causará que el SP falle en la validación de usuario/rol")
        
        # Validar que sea un rol de validación
        if id_rol not in [4, 5, 6, 7, 8, 9]:
            return {
                "success": False,
                "error": "Solo los roles de validación pueden usar esta función"
            }
        
        # Obtener datos del request
        body = await request.json()
        periodo_id = body.get("periodo")
        motivo = body.get("motivo", "").strip()
        
        if not motivo:
            return {
                "success": False,
                "error": "El motivo del rechazo es obligatorio"
            }
        
        # Obtener host
        host_sp = get_request_host(request)
        
        print(f"\n{'='*60}")
        print(f"❌ RECHAZO DE MATRÍCULA - ROL {id_rol}")
        print(f"{'='*60}")
        print(f"Usuario: {usuario_sp}")
        print(f"Periodo ID: {periodo_id}")
        print(f"Unidad Académica ID: {id_unidad_academica}")
        print(f"Host: {host_sp}")
        print(f"Motivo: {motivo}")
        
        # Convertir período a literal si viene como ID
        if str(periodo_id).isdigit():
            periodo_obj = db.query(Periodo).filter(Periodo.Id_Periodo == int(periodo_id)).first()
            if periodo_obj:
                periodo_literal = periodo_obj.Periodo
                print(f"🔄 Período convertido de ID {periodo_id} → '{periodo_literal}'")
            else:
                _, periodo_literal = get_ultimo_periodo(db)
                if not periodo_literal:
                    return {"success": False, "error": "No se pudo obtener un periodo válido"}
                print(f"⚠️ ID de período no encontrado, usando último periodo: '{periodo_literal}'")
        else:
            periodo_literal = str(periodo_id)
            print(f"✅ Período en literal: '{periodo_literal}'")
        
        # Obtener sigla de la unidad académica
        unidad = db.query(Unidad_Academica).filter(
            Unidad_Academica.Id_Unidad_Academica == id_unidad_academica
        ).first()
        unidad_sigla = unidad.Sigla if unidad else ''
        
        if not unidad_sigla:
            return {
                "success": False,
                "error": "No se pudo obtener la Unidad Académica"
            }
        
        print(f"📋 Unidad Académica: {unidad_sigla}")
        
        # Construir nota completa con el nombre completo del usuario para información
        nota_completa = f"{motivo}"
        
        print(f"📝 Nota completa: {nota_completa}")
        
        # EJECUTAR SP_Rechaza_Matricula
        print(f"\n🚀 Ejecutando SP_Rechaza_Matricula...")
        print(f"   @PPeriodo = '{periodo_literal}'")
        print(f"   @UUnidad_Academica = '{unidad_sigla}'")
        print(f"   @UUsuario = '{usuario_sp}' (LOGIN del usuario)")
        print(f"   @HHost = '{host_sp}'")
        print(f"   @NNota = '{nota_completa[:50]}...'")
        
        execute_sp_rechaza_matricula(
            db,
            periodo=periodo_literal,
            unidad_sigla=unidad_sigla,
            usuario=usuario_sp,
            host=host_sp,
            nivel=request.cookies.get('id_nivel', 'No disponible'),
            nota=nota_completa
        )
        
        print(f"✅ Matrícula rechazada exitosamente")
        
        return {
            "success": True,
            "mensaje": f"Matrícula rechazada",
            "data": {
                "rechazado_por": nombre_completo,
                "usuario_login": usuario_sp,
                "id_usuario": id_usuario,
                "id_rol": id_rol,
                "motivo": motivo,
                "fecha_rechazo": datetime.now().isoformat(),
                "periodo": periodo_literal,
                "unidad_academica": unidad_sigla
            }
        }
        
    except Exception as e:
        print(f"\n❌ ERROR al rechazar semestre (rol): {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": f"Error al rechazar el semestre: {str(e)}"
        }


@router.get('/resumen-seleccion')
async def resumen_matricula_seleccion_view(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Vista de selección de filtros para el resumen dinámico de matrícula.
    Permite seleccionar: Periodo, Nivel y Unidad Académica.
    Accesible para roles superiores (6, 7, 8, 9).
    """
    # Obtener datos del usuario logueado
    id_rol = int(sess.id_rol)
    nombre_rol = sess.nombre_rol
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Validar que el usuario tenga rol superior
    roles_permitidos = [1, 4, 5, 6, 7, 8, 9]  # Admin y roles superiores
    if id_rol not in roles_permitidos:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Acceso denegado: Su rol ({nombre_rol}) no tiene permisos para acceder a esta funcionalidad.",
            "redirect_url": "/mod_principal/"
        })

    # Determinar tipo de rol para la vista diferenciada
    # Roles 4-5 (Director/Subdirector de UA): solo ven su propia UA, sin selector de UA
    # Roles 6-9 (Superiores): pueden ver y filtrar por cualquier UA
    es_rol_director_nivel = id_rol in [4, 5]
    es_rol_superior = id_rol in [1, 6, 7, 8, 9]

    # Leer datos de la UA del usuario logueado (guardados en cookies al hacer login)
    id_unidad_academica_usuario = int(sess.id_unidad_academica)
    sigla_unidad_academica_usuario = sess.sigla_unidad_academica

    print(f"\n{'='*60}")
    print(f"VISTA DE SELECCIÓN - RESUMEN DINÁMICO DE MATRÍCULA")
    print(f"Usuario: {nombre_completo}")
    print(f"Rol: {nombre_rol} (ID: {id_rol}) | es_rol_director_nivel={es_rol_director_nivel}")
    print(f"UA del usuario: {sigla_unidad_academica_usuario} (ID: {id_unidad_academica_usuario})")
    print(f"{'='*60}")

    # Obtener periodo activo o, en su defecto, el último
    periodo_activo_id, periodo_activo_literal = get_periodo_activo(db)
    if not periodo_activo_id:
        periodo_activo_id, periodo_activo_literal = get_ultimo_periodo(db)

    # Obtener todos los periodos disponibles
    periodos = db.query(Periodo).filter(Periodo.Id_Estatus == 1).order_by(Periodo.Id_Periodo.desc()).all()

    # Obtener todas las unidades académicas con su nivel desde SemaforoUnidadAcademica
    from sqlalchemy import distinct
    unidades_con_nivel = db.query(
        Unidad_Academica,
        SemaforoUnidadAcademica.Id_Nivel
    ).join(
        SemaforoUnidadAcademica,
        Unidad_Academica.Id_Unidad_Academica == SemaforoUnidadAcademica.Id_Unidad_Academica
    ).filter(
        Unidad_Academica.Id_Estatus == 1
    ).distinct().order_by(Unidad_Academica.Nombre).all()

    # Crear estructura de unidades con sus niveles
    unidades_dict = {}
    for ua, id_nivel in unidades_con_nivel:
        if ua.Id_Unidad_Academica not in unidades_dict:
            unidades_dict[ua.Id_Unidad_Academica] = {
                'Id_Unidad_Academica': ua.Id_Unidad_Academica,
                'Siglas': ua.Sigla,
                'Nombre_Unidad_Academica': ua.Nombre,
                'niveles': []
            }
        if id_nivel not in unidades_dict[ua.Id_Unidad_Academica]['niveles']:
            unidades_dict[ua.Id_Unidad_Academica]['niveles'].append(id_nivel)

    # Convertir a lista y ordenar alfabéticamente por nombre
    unidades = sorted(unidades_dict.values(), key=lambda x: x['Nombre_Unidad_Academica'])

    # Para roles 4-5: filtrar niveles a solo los que corresponden a su UA
    if es_rol_director_nivel and id_unidad_academica_usuario:
        id_niveles_mi_ua = []
        mi_ua_info = unidades_dict.get(id_unidad_academica_usuario)
        if mi_ua_info:
            id_niveles_mi_ua = mi_ua_info['niveles']

        niveles = db.query(Nivel).filter(
            Nivel.Id_Estatus == 1,
            Nivel.Id_Nivel.in_(id_niveles_mi_ua)
        ).order_by(Nivel.Id_Nivel).all()

        mi_unidad_nombre = mi_ua_info['Nombre_Unidad_Academica'] if mi_ua_info else sigla_unidad_academica_usuario
        print(f"✅ Roles 4-5: niveles filtrados a UA '{sigla_unidad_academica_usuario}' → {len(niveles)} niveles disponibles")
    else:
        # Roles 6-9 y admin: todos los niveles
        niveles = db.query(Nivel).filter(Nivel.Id_Estatus == 1).order_by(Nivel.Id_Nivel).all()
        mi_unidad_nombre = ""

    print(f"✅ Cargadas {len(unidades)} unidades académicas")
    print(f"✅ Cargados {len(niveles)} niveles")

    return templates.TemplateResponse("matricula_resumen_seleccion.html", {
        "request": request,
        "nombre_usuario": nombre_completo,
        "nombre_rol": nombre_rol,
        "periodos": periodos,
        "periodo_activo_id": periodo_activo_id,
        "periodo_activo_literal": periodo_activo_literal,
        "niveles": niveles,
        "unidades": unidades,
        # Flags de rol para la vista diferenciada
        "es_rol_director_nivel": es_rol_director_nivel,
        "es_rol_superior": es_rol_superior,
        # Datos de la UA del usuario (usados solo para roles 4-5)
        "mi_unidad_sigla": sigla_unidad_academica_usuario,
        "mi_unidad_nombre": mi_unidad_nombre,
    })


@router.get('/resumen-dinamico')
async def resumen_matricula_dinamico_view(
    request: Request, 
    periodo: str,
    nivel: str,
    unidad: str, sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Vista de resumen dinámico de matrícula con estructura adaptativa según los semestres de la UA.
    Muestra por Programa → Modalidad → Semestres → Tipo de Ingreso (H/M/T).
    - Semestre 1: Nuevo Ingreso + Repetidores
    - Semestres 2+: Reingreso + Repetidores
    """
    # Obtener datos del usuario logueado
    id_rol = int(sess.id_rol)
    nombre_rol = sess.nombre_rol
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))

    # Validar que el usuario tenga rol superior
    roles_permitidos = [1, 4, 5, 6, 7, 8, 9]
    if id_rol not in roles_permitidos:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Acceso denegado: Su rol ({nombre_rol}) no tiene permisos para acceder a esta funcionalidad.",
            "redirect_url": "/mod_principal/"
        })

    print(f"\n{'='*60}")
    print(f"RESUMEN DINÁMICO DE MATRÍCULA")
    print(f"Periodo: {periodo}, Nivel: {nivel}, Unidad: {unidad}")
    print(f"{'='*60}")

    try:
        # Obtener datos del SP
        host = get_request_host(request)
        usuario_login = sess.usuario
        
        from backend.crud.Matricula import execute_sp_consulta_matricula
        rows, columns, nota_rechazo = execute_sp_consulta_matricula(
            db, unidad, periodo, nivel, usuario_login, host
        )

        if not rows:
            return templates.TemplateResponse("matricula_resumen_dinamico.html", {
                "request": request,
                "nombre_usuario": nombre_completo,
                "nombre_rol": nombre_rol,
                "periodo": periodo,
                "nivel": nivel,
                "unidad": unidad,
                "datos_resumen": [],
                "max_semestres": 0,
                "datos_edad_turno": [],
                "turnos_ordenados": [],
                "subtotales_modalidad": [],
                "subtotales_turno": [],
                "error_message": "No hay datos disponibles para los filtros seleccionados"
            })

        # === PROCESAR DATOS PARA EL RESUMEN DINÁMICO ===
        # Mapeo de nombres de semestres a números
        semestre_map = {
            'Primero': 1, 'Primer': 1, '1': 1, 1: 1,
            'Segundo': 2, '2': 2, 2: 2,
            'Tercero': 3, 'Tercer': 3, '3': 3, 3: 3,
            'Cuarto': 4, '4': 4, 4: 4,
            'Quinto': 5, '5': 5, 5: 5,
            'Sexto': 6, '6': 6, 6: 6,
            'Septimo': 7, 'Séptimo': 7, '7': 7, 7: 7,
            'Octavo': 8, '8': 8, 8: 8,
            'Noveno': 9, '9': 9, 9: 9,
            'Decimo': 10, 'Décimo': 10, '10': 10, 10: 10,
            'Decimo primero': 11, 'Once': 11, '11': 11, 11: 11,
            'Decimo segundo': 12, 'Doce': 12, '12': 12, 12: 12
        }
        
        # Función para convertir semestre a número
        def convertir_semestre(sem_value):
            if isinstance(sem_value, int):
                return sem_value
            if isinstance(sem_value, str):
                # Intentar convertir directamente a int
                try:
                    return int(sem_value)
                except ValueError:
                    # Buscar en el mapeo
                    return semestre_map.get(sem_value.strip(), 0)
            return 0
        
        # 1. Detectar el máximo de semestres
        max_semestres = max([convertir_semestre(row.get('Semestre', 0)) for row in rows])
        
        print(f"📊 Máximo de semestres detectado: {max_semestres}")
        print(f"📊 Total de filas del SP: {len(rows)}")
        print(f"📊 Columnas disponibles: {columns if columns else list(rows[0].keys()) if rows else 'N/A'}")
        
        # Mostrar una muestra de los primeros registros
        if rows:
            print(f"📋 Muestra de datos (primeros 3 registros):")
            for i, row in enumerate(rows[:3]):
                print(f"   Fila {i+1}:")
                print(f"      Todas las claves: {list(row.keys())}")
                print(f"      Programa='{row.get('Programa')}', Nombre_Programa='{row.get('Nombre_Programa')}'")
                print(f"      Modalidad='{row.get('Modalidad')}', Semestre='{row.get('Semestre')}'")
                print(f"      Matricula={row.get('Matricula')}, Total_Grupos={row.get('Total_Grupos')}")

        # 2. Agrupar por Programa y Modalidad
        from collections import defaultdict
        
        # Crear estructura con tipos explícitos
        def crear_estructura_modalidad():
            return {
                'semestres': defaultdict(lambda: defaultdict(lambda: {'H': 0, 'M': 0, 'T': 0})),
                'grupos': set(),
                'total_h': 0,
                'total_m': 0,
                'total_t': 0
            }
        
        estructura = defaultdict(lambda: defaultdict(crear_estructura_modalidad))

        filas_procesadas = 0
        filas_descartadas = 0
        
        for row in rows:
            # Intentar diferentes nombres de columna para el programa
            programa = (row.get('Programa') or 
                       row.get('Nombre_Programa') or 
                       row.get('Programa_Academico') or 
                       row.get('Nombre') or 
                       'Sin Programa')
            
            # Si es None o string vacío, usar 'Sin Programa'
            if not programa or (isinstance(programa, str) and programa.strip() == ''):
                programa = 'Sin Programa'
            
            modalidad = row.get('Modalidad', 'Sin Modalidad')
            if not modalidad or (isinstance(modalidad, str) and modalidad.strip() == ''):
                modalidad = 'Sin Modalidad'
                
            semestre = convertir_semestre(row.get('Semestre', 0))
            tipo_ingreso = row.get('Tipo_de_Ingreso', '')
            sexo = row.get('Sexo', '')
            
            # Manejar valores None en campos numéricos
            matricula_value = row.get('Matricula', 0)
            matricula = int(matricula_value) if matricula_value is not None else 0
            
            total_grupos_value = row.get('Total_Grupos', 0)
            total_grupos = int(total_grupos_value) if total_grupos_value is not None else 0
            
            # Saltar filas sin datos válidos
            if semestre == 0:
                filas_descartadas += 1
                print(f"⚠️ Fila descartada (semestre=0): Programa='{programa}', Semestre={row.get('Semestre')}")
                continue
            
            if not programa or programa.strip() == '':
                filas_descartadas += 1
                print(f"⚠️ Fila descartada (programa vacío): Programa='{programa}'")
                continue
            
            filas_procesadas += 1

            # Normalizar tipo de ingreso
            # Semestre 1: Nuevo Ingreso o Repetidores
            # Semestres 2+: Reingreso o Repetidores
            if semestre == 1:
                if 'Nuevo' in tipo_ingreso or 'nuevo' in tipo_ingreso.lower():
                    tipo_normalizado = 'Nuevo Ingreso'
                elif 'Repetidor' in tipo_ingreso or 'repetidor' in tipo_ingreso.lower():
                    tipo_normalizado = 'Repetidores'
                else:
                    tipo_normalizado = tipo_ingreso
            else:
                if 'Reingreso' in tipo_ingreso or 'reingreso' in tipo_ingreso.lower():
                    tipo_normalizado = 'Reingreso'
                elif 'Repetidor' in tipo_ingreso or 'repetidor' in tipo_ingreso.lower():
                    tipo_normalizado = 'Repetidores'
                else:
                    tipo_normalizado = tipo_ingreso

            # Almacenar datos
            if sexo == 'Hombre':
                estructura[programa][modalidad]['semestres'][semestre][tipo_normalizado]['H'] += matricula
                estructura[programa][modalidad]['total_h'] += matricula
            elif sexo == 'Mujer':
                estructura[programa][modalidad]['semestres'][semestre][tipo_normalizado]['M'] += matricula
                estructura[programa][modalidad]['total_m'] += matricula

            # Actualizar totales
            estructura[programa][modalidad]['semestres'][semestre][tipo_normalizado]['T'] += matricula
            estructura[programa][modalidad]['total_t'] += matricula

            # Almacenar grupos únicos usando una clave compuesta
            # Asumiendo que cada fila tiene información de grupo único
            grupo_key = f"{programa}|{modalidad}|{semestre}|{row.get('Turno', '')}|{total_grupos}"
            if total_grupos > 0:
                estructura[programa][modalidad]['grupos'].add(grupo_key)

        print(f"✅ Filas procesadas: {filas_procesadas}")
        print(f"⚠️ Filas descartadas: {filas_descartadas}")
        print(f"📊 Programas únicos encontrados: {len(estructura)}")

        # 3. Calcular el total de grupos de toda la UA (sin duplicar)
        grupos_totales_ua = set()
        for programa in estructura:
            for modalidad in estructura[programa]:
                grupos_unicos = estructura[programa][modalidad]['grupos']
                # Agregar todos los grupos al conjunto global
                grupos_totales_ua.update(grupos_unicos)
        
        total_grupos_ua = len(grupos_totales_ua)
        print(f"📊 Total de grupos de la UA: {total_grupos_ua}")

        # 4. Convertir estructura a lista para el template
        datos_resumen = []
        for programa, modalidades in estructura.items():
            for modalidad, datos in modalidades.items():
                # Construir semestres con sus tipos de ingreso
                semestres_data = []
                for sem in range(1, max_semestres + 1):
                    if sem == 1:
                        tipos = ['Nuevo Ingreso', 'Repetidores']
                    else:
                        tipos = ['Reingreso', 'Repetidores']
                    
                    sem_info = {'numero': sem, 'tipos': []}
                    for tipo in tipos:
                        tipo_data = datos['semestres'][sem].get(tipo, {'H': 0, 'M': 0, 'T': 0})
                        sem_info['tipos'].append({
                            'nombre': tipo,
                            'H': tipo_data['H'],
                            'M': tipo_data['M'],
                            'T': tipo_data['T']
                        })
                    semestres_data.append(sem_info)

                datos_resumen.append({
                    'programa': programa,
                    'modalidad': modalidad,
                    'semestres': semestres_data,
                    'total_h': datos['total_h'],
                    'total_m': datos['total_m'],
                    'total_t': datos['total_t']
                })

        # Ordenar por programa y modalidad
        datos_resumen.sort(key=lambda x: (x['programa'], x['modalidad']))

        print(f"✅ Resumen procesado (Tabla 1 - Programa x Modalidad): {len(datos_resumen)} filas")

        # ========================================
        # PROCESAR TABLA 2: PROGRAMA X EDAD X TURNO
        # ========================================
        print(f"\n{'='*60}")
        print(f"PROCESANDO TABLA 2: PROGRAMA X EDAD X TURNO")
        print(f"{'='*60}")
        
        # Crear estructura anidada: programa → edad → turno → H/M/T
        estructura_programa_edad = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'H': 0, 'M': 0, 'T': 0})))
        programas_set = set()
        edades_set = set()
        turnos_set = set()
        
        filas_edad_procesadas = 0
        filas_edad_descartadas = 0
        
        for row in rows:
            # Obtener programa (igual que en Tabla 1)
            programa = (row.get('Programa') or 
                       row.get('Nombre_Programa') or 
                       row.get('Programa_Academico') or 
                       row.get('Nombre') or 
                       'Sin Programa')
            
            if not programa or (isinstance(programa, str) and programa.strip() == ''):
                programa = 'Sin Programa'
            
            edad_raw = row.get('Grupo_Edad', None)
            turno_raw = row.get('Turno', None)
            sexo = row.get('Sexo', '')
            
            # Manejar valores None en campos numéricos
            matricula_value = row.get('Matricula', 0)
            matricula = int(matricula_value) if matricula_value is not None else 0
            
            # Solo procesar filas que tengan programa, edad Y turno definidos
            if not programa or not edad_raw or not turno_raw:
                filas_edad_descartadas += 1
                continue
            
            edad = str(edad_raw).strip()
            turno = str(turno_raw).strip()
            
            # Verificar que no sean strings vacíos después del strip
            if not edad or not turno:
                filas_edad_descartadas += 1
                continue
            
            filas_edad_procesadas += 1
            programas_set.add(programa)
            edades_set.add(edad)
            turnos_set.add(turno)
            
            # Acumular datos por turno
            if sexo == 'Hombre':
                estructura_programa_edad[programa][edad][turno]['H'] += matricula
            elif sexo == 'Mujer':
                estructura_programa_edad[programa][edad][turno]['M'] += matricula
            
            estructura_programa_edad[programa][edad][turno]['T'] += matricula
        
        print(f"✅ Filas procesadas (Tabla 2): {filas_edad_procesadas}")
        print(f"⚠️ Filas descartadas (Tabla 2): {filas_edad_descartadas}")
        print(f"📊 Programas únicos: {len(programas_set)} - {sorted(list(programas_set))}")
        print(f"📊 Edades únicas: {len(edades_set)} - {sorted(list(edades_set))}")
        print(f"📊 Turnos únicos: {len(turnos_set)} - {sorted(list(turnos_set))}")
        
        # Ordenar programas, edades y turnos
        programas_ordenados = sorted(list(programas_set))
        edades_ordenadas = sorted(list(edades_set))
        turnos_ordenados = sorted(list(turnos_set))
        
        # Convertir estructura a lista para el template
        # Formato: [{programa, edad, turnos: [{turno, H, M, T}], total_h, total_m, total_t}]
        datos_edad_turno = []
        
        if programas_ordenados and edades_ordenadas and turnos_ordenados:
            for programa in programas_ordenados:
                for edad in edades_ordenadas:
                    # Construir datos de turnos para esta combinación programa-edad
                    turnos_data = []
                    total_h = 0
                    total_m = 0
                    total_t = 0
                    
                    for turno in turnos_ordenados:
                        datos_turno = estructura_programa_edad[programa][edad].get(turno, {'H': 0, 'M': 0, 'T': 0})
                        turnos_data.append({
                            'turno': turno,
                            'H': datos_turno['H'],
                            'M': datos_turno['M'],
                            'T': datos_turno['T']
                        })
                        total_h += datos_turno['H']
                        total_m += datos_turno['M']
                        total_t += datos_turno['T']
                    
                    # Solo agregar si hay datos (al menos un turno con matrícula > 0)
                    if total_t > 0:
                        datos_edad_turno.append({
                            'programa': programa,
                            'edad': edad,
                            'turnos': turnos_data,
                            'total_h': total_h,
                            'total_m': total_m,
                            'total_t': total_t
                        })
        
        print(f"✅ Tabla 2 procesada: {len(datos_edad_turno)} filas (programa × edad)")

        # ========================================
        # CALCULAR SUBTOTALES POR MODALIDAD (TABLA 1)
        # ========================================
        print(f"\n{'='*60}")
        print(f"CALCULANDO SUBTOTALES POR MODALIDAD")
        print(f"{'='*60}")
        
        subtotales_modalidad = defaultdict(lambda: {'H': 0, 'M': 0, 'T': 0})
        modalidades_tabla1 = set()
        
        for dato in datos_resumen:
            modalidad = dato['modalidad']
            modalidades_tabla1.add(modalidad)
            subtotales_modalidad[modalidad]['H'] += dato['total_h']
            subtotales_modalidad[modalidad]['M'] += dato['total_m']
            subtotales_modalidad[modalidad]['T'] += dato['total_t']
        
        # Convertir a lista ordenada
        subtotales_modalidad_lista = []
        for modalidad in sorted(list(modalidades_tabla1)):
            subtotales_modalidad_lista.append({
                'modalidad': modalidad,
                'H': subtotales_modalidad[modalidad]['H'],
                'M': subtotales_modalidad[modalidad]['M'],
                'T': subtotales_modalidad[modalidad]['T']
            })
        
        print(f"✅ Subtotales calculados para {len(subtotales_modalidad_lista)} modalidades")

        # ========================================
        # CALCULAR SUBTOTALES POR TURNO (TABLA 2)
        # ========================================
        print(f"\n{'='*60}")
        print(f"CALCULANDO SUBTOTALES POR TURNO")
        print(f"{'='*60}")
        
        subtotales_turno = []
        if turnos_ordenados:
            for turno in turnos_ordenados:
                total_h = 0
                total_m = 0
                total_t = 0
                
                # Sumar todos los valores de este turno a través de todos los programas y edades
                for programa in programas_ordenados:
                    for edad in edades_ordenadas:
                        datos_turno = estructura_programa_edad[programa][edad].get(turno, {'H': 0, 'M': 0, 'T': 0})
                        total_h += datos_turno['H']
                        total_m += datos_turno['M']
                        total_t += datos_turno['T']
                
                subtotales_turno.append({
                    'turno': turno,
                    'H': total_h,
                    'M': total_m,
                    'T': total_t
                })
        
        print(f"✅ Subtotales calculados para {len(subtotales_turno)} turnos")

        # ========================================
        # VERIFICAR ESTADO DE VALIDACIÓN DEL USUARIO (solo para roles 4-5)
        # ========================================
        usuario_ya_valido = False
        usuario_ya_rechazo = False
        puede_validar = False
        esperando_por_rol = None
        
        if id_rol in [4, 5, 6, 7, 8, 9]:
            # Obtener ID del periodo
            periodo_obj = db.query(Periodo).filter(Periodo.Periodo == periodo).first()
            if periodo_obj:
                periodo_id = periodo_obj.Id_Periodo
            else:
                periodo_id, _ = get_ultimo_periodo(db)
                if not periodo_id:
                    periodo_id = 1
            
            # Obtener ID de la unidad académica
            ua_obj = db.query(Unidad_Academica).filter(Unidad_Academica.Nombre == unidad).first()
            if not ua_obj:
                # Intentar por sigla
                ua_obj = db.query(Unidad_Academica).filter(Unidad_Academica.Sigla == unidad).first()
            
            id_unidad_academica = ua_obj.Id_Unidad_Academica if ua_obj else 0
            
            # Obtener ID del nivel
            nivel_obj = db.query(Nivel).filter(Nivel.Nivel == nivel).first()
            id_nivel = nivel_obj.Id_Nivel if nivel_obj else 0
            
            id_usuario_actual = int(sess.id_usuario)
            
            print(f"\n🔍 Verificando estado de validación para usuario {id_usuario_actual}...")
            print(f"   Periodo ID: {periodo_id}, UA ID: {id_unidad_academica}, Nivel ID: {id_nivel}")
            
            # Verificar estado del semáforo de la UA
            semaforo_unidad = db.query(SemaforoUnidadAcademica).filter(
                SemaforoUnidadAcademica.Id_Periodo == periodo_id,
                SemaforoUnidadAcademica.Id_Unidad_Academica == id_unidad_academica,
                SemaforoUnidadAcademica.Id_Nivel == id_nivel,
                SemaforoUnidadAcademica.Id_Formato == 1  # Formato de matrícula
            ).first()
            
            if semaforo_unidad:
                estado_semaforo = semaforo_unidad.Id_Semaforo
                print(f"   📊 Estado del semáforo: {estado_semaforo}")
                
                # Lógica: El usuario puede validar si el semáforo está en (id_rol - 1)
                semaforo_esperado = id_rol - 1
                print(f"   ⚖️ Semáforo esperado para rol {id_rol}: {semaforo_esperado}")
                
                if estado_semaforo == semaforo_esperado:
                    puede_validar = True
                    print(f"   ✅ Usuario PUEDE validar (semáforo en nivel correcto)")
                elif estado_semaforo >= id_rol:
                    usuario_ya_valido = True
                    puede_validar = False
                    print(f"   🔒 Usuario YA validó (semáforo >= {id_rol})")
                else:
                    puede_validar = False
                    try:
                        # Semáforo 1-2 siempre esperan por Capturista
                        if estado_semaforo in [1, 2]:
                            esperando_por_rol = "Capturista"
                        else:
                            rol_esperado_id = int(estado_semaforo) + 1
                            rol_obj = db.query(CatRoles).filter(CatRoles.Id_Rol == rol_esperado_id).first()
                            esperando_por_rol = rol_obj.Rol if rol_obj else "Capturista"
                    except Exception:
                        esperando_por_rol = "Capturista"
                    print(f"   ⏳ Usuario debe esperar (semáforo en nivel {estado_semaforo})")
            else:
                esperando_por_rol = "Capturista"
                print(f"   ⚠️ No se encontró semáforo para esta UA/Nivel/Periodo")
            
            # Verificar si el usuario rechazó esta matrícula
            validacion_rechazo = db.query(Validacion).filter(
                Validacion.Id_Periodo == periodo_id,
                Validacion.Id_Usuario == id_usuario_actual,
                Validacion.Id_Formato == 1,
                Validacion.Validado == 0  # Rechazo
            ).first()
            
            if validacion_rechazo:
                if not (semaforo_unidad and estado_semaforo == (id_rol - 1)):
                    usuario_ya_rechazo = True
                    puede_validar = False
                    print(f"   ❌ Usuario YA rechazó esta matrícula")
            
            print(f"\n📤 Estado final:")
            print(f"   puede_validar: {puede_validar}")
            print(f"   usuario_ya_valido: {usuario_ya_valido}")
            print(f"   usuario_ya_rechazo: {usuario_ya_rechazo}")

        return templates.TemplateResponse("matricula_resumen_dinamico.html", {
            "request": request,
            "nombre_usuario": nombre_completo,
            "nombre_rol": nombre_rol,
            "id_rol": id_rol,
            "periodo": periodo,
            "nivel": nivel,
            "unidad": unidad,
            "datos_resumen": datos_resumen,
            "max_semestres": max_semestres,
            "total_grupos_ua": total_grupos_ua,
            "datos_edad_turno": datos_edad_turno,
            "turnos_ordenados": turnos_ordenados,
            "subtotales_modalidad": subtotales_modalidad_lista,
            "subtotales_turno": subtotales_turno,
            "error_message": None,
            "puede_validar": puede_validar,
            "usuario_ya_valido": usuario_ya_valido,
            "usuario_ya_rechazo": usuario_ya_rechazo,
            "esperando_por_rol": esperando_por_rol
        })

    except Exception as e:
        print(f"❌ Error al generar resumen dinámico: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return templates.TemplateResponse("matricula_resumen_dinamico.html", {
            "request": request,
            "nombre_usuario": nombre_completo,
            "nombre_rol": nombre_rol,
            "periodo": periodo,
            "nivel": nivel,
            "unidad": unidad,
            "datos_resumen": [],
            "max_semestres": 0,
            "datos_edad_turno": [],
            "turnos_ordenados": [],
            "totales_edad_turno": {},
            "subtotales_modalidad": [],
            "subtotales_edad": [],
            "error_message": f"Error al procesar el resumen: {str(e)}"
        })

