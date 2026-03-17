from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime

from backend.database import db_base
from backend.database.models.Temp_Aprovechamiento import Temp_Aprovechamiento
from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.periodo_service import get_periodo_activo, get_periodo_anterior_al_ultimo, get_todos_los_periodos
from backend.services.aprovechamiento_service import get_unidades_con_niveles_asociados
from backend.database.models.CatPeriodo import CatPeriodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.database.models.CatNivel import CatNivel
from backend.database.models.CatSemaforo import CatSemaforo
from backend.database.models.Validacion import Validacion
from backend.database.models.SemaforoUnidadAcademica import SemaforoUnidadAcademica
from backend.services.nivel_service import get_niveles_by_unidad_academica
from backend.core.auth import get_current_session

router = APIRouter()

# Variable global
HHost: str = "Test"


# Función auxiliar para obtener host
def get_request_host(request: Request) -> str:
    """
    Obtiene el host (IP) de la solicitud.
    """
    client_host = request.client.host if request.client else "127.0.0.1"
    return client_host



@router.get("/consulta", response_class=HTMLResponse)
def aprovechamiento_view(
    request: Request,
    sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    # 1. Preparación de variables desde cookies
    
    Rol = str(getattr(sess, 'nombre_rol', '') or '')
    UUsuario = getattr(sess, 'usuario', '') or ''
    UUnidad_Academica = str(getattr(sess, 'sigla_unidad_academica', '') or '')
    NNivel = str(getattr(sess, 'nombre_nivel', '') or '')
    HHost = request.client.host
    periodo_literal = get_periodo_activo(db)
    PPeriodo = periodo_literal[1]
    ID_PPeriodo = periodo_literal[0]
    periodo_aprovechamiento = PPeriodo
    Id_Unidad_Academica = int(getattr(sess, 'id_unidad_academica', 0) or 0)
    nombre_completo = getattr(sess, 'nombre_completo', '')
 

    if Rol == "Capturista":
        
        aprovechamientos_limpios = []
        reincorporados_detallados = [] 
        inscritos_final = []
        rama = ""

        try:
            # --- SP 1: Aprovechamiento ---
            query_aprov = text("""
                SET NOCOUNT ON;
                EXEC dbo.SP_Consulta_Aprovechamiento_Unidad_Academica
                    @UUnidad_Academica = :UUnidad_Academica, 
                    @PPeriodo = :PPeriodo,
                    @NNivel = :NNivel, 
                    @UUsuario = :UUsuario, 
                    @HHost = :HHost;
            """)
            
            result_aprov = db.execute(query_aprov, {
                "UUnidad_Academica": UUnidad_Academica, 
                "PPeriodo": PPeriodo,
                "NNivel": NNivel, 
                "UUsuario": UUsuario, 
                "HHost": HHost
            })

            if result_aprov.returns_rows:
                aprovechamientos_raw = [dict(row) for row in result_aprov.mappings().all()]
            else:
                aprovechamientos_raw = []

            if aprovechamientos_raw:
                
                # Determinamos si todos los semáforos están en nivel 3
                todos_en_tres = all(str(reg.get("Id_Semaforo")) == "3" for reg in aprovechamientos_raw)
                
                if todos_en_tres:
                    Periodoant = get_periodo_anterior_al_ultimo(db)
                    Id_Periodo_anterior = Periodoant[0]
                    semaforoUA = db.query(SemaforoUnidadAcademica).filter(SemaforoUnidadAcademica.Id_Periodo==Id_Periodo_anterior, SemaforoUnidadAcademica.Id_Unidad_Academica==Id_Unidad_Academica, SemaforoUnidadAcademica.Id_Formato==2).first()
                    db.commit()
                    if semaforoUA.Id_Semaforo == 2:
                        # 1. Preparamos el query una sola vez (es más eficiente)
                        query_finaliza = text("""
                            SET NOCOUNT ON;
                            EXEC [dbo].[SP_Finaliza_Captura_Aprovechamiento] 
                                @PPeriodo = :PPeriodo,
                                @UUnidad_Academica = :UUnidad_Academica,
                                @MModalidad = :MModalidad,
                                @PPrograma = :PPrograma,
                                @SSemestre = :SSemestre,
                                @UUsuario = :UUsuario,
                                @HHost = :HHost,
                                @NNivel = :NNivel;
                        """)
                        # 2. Creamos un 'set' vacío para llevar el registro de lo que ya procesamos
                        combinaciones_procesadas = set()

                        # 3. Iteramos sobre los datos que trajo el primer SP
                        for reg in aprovechamientos_raw:
                            # Extraemos los valores. 
                            # ¡OJO!: Cambia "Modalidad", "Programa" y "Semestre" por los nombres EXACTOS de las columnas que devuelve tu BD.
                            m_modalidad = reg.get("Modalidad", "") 
                            p_programa = reg.get("Nombre_Programa", "")
                            s_semestre = reg.get("Semestre", "")

                            # Creamos una tupla con esta combinación
                            combinacion_actual = (m_modalidad, p_programa, s_semestre)

                            # 4. Validamos si esta combinación es única
                            if combinacion_actual not in combinaciones_procesadas:
                                # Como es nueva, la agregamos a nuestro registro para no repetirla luego
                                combinaciones_procesadas.add(combinacion_actual)
                                
                                #print(f"Ejecutando SP para: Modalidad={m_modalidad}, Programa={p_programa}, Semestre={s_semestre}")
                                
                                # 5. Ejecutamos el SP con los datos únicos
                                db.execute(query_finaliza, {
                                    "PPeriodo": PPeriodo,
                                    "UUnidad_Academica": UUnidad_Academica,
                                    "MModalidad": m_modalidad,
                                    "PPrograma": p_programa,
                                    "SSemestre": s_semestre,
                                    "UUsuario": UUsuario,
                                    "HHost": HHost,
                                    "NNivel": NNivel
                                })
                        
                        # 6. MUY IMPORTANTE: Guardar los cambios en la base de datos después del bucle
                        try:
                            db.commit()
                            #print("Todos los SP se ejecutaron y guardaron correctamente.")
                        except Exception as e:
                            db.rollback() # Si algo falla, revertimos para no dejar datos a medias
                            print(f"Error al guardar los cambios en BD: {e}")

                
                # --- Continuación de tu lógica original ---
                rama = aprovechamientos_raw[0].get("Nombre_Rama", "")
                periodo_aprovechamiento = aprovechamientos_raw[0].get("Periodo")

                for reg in aprovechamientos_raw:
                    reg.pop("Periodo", None)
                    situacion = str(reg.get("Aprovechamiento", "")).strip().lower()
                    if situacion == "reincorporados":
                        reincorporados_detallados.append(reg)
                    else:
                        aprovechamientos_limpios.append(reg)

        except Exception as e:
            print(f"--- ERROR DETECTADO ---")
            print(f"Mensaje: {e}")
            
        
        return templates.TemplateResponse(
            "aprovechamiento_consulta.html",
            {   
                "rol": Rol,
                "nombre_usuario": nombre_completo,
                "periodo": periodo_aprovechamiento,
                "unidad_academica": UUnidad_Academica,
                "request": request,
                "aprovechamientos": aprovechamientos_limpios,
                "inscritos": inscritos_final,
                "reincorporados": reincorporados_detallados, 
                "rama": rama
            }
        )
    elif Rol == "CEGET" or Rol == "Titular":
        niveles = get_niveles_by_unidad_academica(db, Id_Unidad_Academica)
        niveles.sort(key=lambda x: x.Id_Nivel)
        return templates.TemplateResponse(  
            "aprovechamiento_selector.html",
            {
                "rol": Rol,
                "nombre_usuario": nombre_completo,
                "periodo_activo_literal": PPeriodo,
                "unidad_academica": UUnidad_Academica,
                "niveles": niveles,
                "request": request
            }
        )
    else:
        todos_los_periodos = get_todos_los_periodos(db)        
        # Obtener unidades con sus niveles asociados (lista de dicts)
        unidades_con_niveles = get_unidades_con_niveles_asociados(db)
        # Obtener catálogos para filtros
        niveles = db.query(CatNivel).all()
        nivel_usuario = str(getattr(sess, 'nombre_nivel', '') or '')
        return templates.TemplateResponse(
            "aprovechamiento_selector.html",
            {
                "rol": Rol,
                "nombre_usuario": nombre_completo,
                "nivel_usuario": nivel_usuario,
                "periodos": todos_los_periodos,
                "periodo_activo_literal": PPeriodo,
                "unidad_academica": UUnidad_Academica,
                "unidades": unidades_con_niveles,
                "niveles": niveles,
                "request": request
            }
        )

@router.post("/guardar_captura_completa")
async def guardar_captura_completa_aprovechamiento(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para guardar la captura completa de aprovechamiento desde el frontend.
    Este endpoint debería ser llamado por tu función JavaScript guardarYActualizarAprovechamiento()
    """
    try:
        data = await request.json()
        print(f"📥 Datos recibidos para guardar: {data}")
        
        # Aquí deberías procesar los datos y guardarlos en Temp_Aprovechamiento
        # Similar a guardar_progreso_aprovechamiento pero con estructura diferente
        
        return {
            "message": "Captura de aprovechamiento guardada exitosamente", 
            "status": "success"
        }
    except Exception as e:
        print(f"❌ Error al guardar captura completa: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al guardar captura: {str(e)}")


@router.post("/guardar_progreso_aprovechamiento")
def guardar_progreso_aprovechamiento(datos: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Guardar el progreso del aprovechamiento en la tabla Temp_Aprovechamiento
    usando forzosamente el periodo anterior al último.
    """
    try:
        # 1. OBTENER EL PERIODO ANTERIOR AL ÚLTIMO
        _, periodo_anterior = get_periodo_anterior_al_ultimo(db)
        print(datos)
        if not periodo_anterior:
            print("⚠️ No se encontró un periodo anterior al último, se usará el enviado por el cliente.")
        else:
            print(f"🎯 Forzando uso de Periodo Anterior: {periodo_anterior}")

        print(f"📥 Recibiendo {len(datos)} registros para guardar...")
        print(f"📥 Datos: {datos}")
        if not datos:
            return {"message": "No hay datos para guardar"}
        
        # Mapeo de nombres de campos
        mapeo_campos = {
            'periodo': 'Periodo', # Se sobreescribirá con periodo_anterior si existe
            'rama': 'Nombre_Rama',
            'unidad_academica': 'Sigla',
            'sigla': 'Sigla',
            'programa': 'Nombre_Programa',
            'modalidad': 'Modalidad',
            'turno': 'Turno',
            'semestre': 'Semestre',
            'situacion_academica': 'Aprovechamiento',
            'aprovechamiento': 'Aprovechamiento',
            'sexo': 'Sexo',
            'alumnos': 'Alumnos',
            'nivel': 'Nivel',
            'id_semaforo': 'id_semaforo'
        }
        
        registros_procesados = 0
        errores = []
        
        for i, dato_original in enumerate(datos):
            try:
                dato_corregido = {}
                for key_original, value in dato_original.items():
                    key_normalizada = key_original.lower().replace(' ', '_')
                    
                    if key_normalizada in mapeo_campos:
                        key_modelo = mapeo_campos[key_normalizada]
                        dato_corregido[key_modelo] = value

                # 2. SOBREESCRITURA CRÍTICA: Forzar el periodo anterior al último
                if periodo_anterior:
                    dato_corregido['Periodo'] = periodo_anterior
                
                # Asegurar campos requeridos que falten en el JSON
                if 'Nombre_Rama' not in dato_corregido:
                    dato_corregido['Nombre_Rama'] = dato_original.get('rama', '')
                
                if 'id_semaforo' not in dato_corregido:
                    dato_corregido['id_semaforo'] = 2

                # UPSERT lógico: Clave única con TODOS los campos excepto 'Alumnos'
                # (mismo patrón que matrícula)
                filtro_unico = {k: v for k, v in dato_corregido.items() if k not in ['Alumnos']}
                
                # Eliminar cualquier registro previo que coincida con esta clave
                if filtro_unico:
                    db.query(Temp_Aprovechamiento).filter_by(**filtro_unico).delete(synchronize_session=False)
                    db.flush()  # Forzar flush para actualizar el identity map antes del insert

                # Crear instancia e insertar
                temp_record = Temp_Aprovechamiento(**dato_corregido)
                db.add(temp_record)
                registros_procesados += 1
                
                # Commit parcial cada 50
                if registros_procesados % 50 == 0:
                    db.commit()
                    
            except Exception as e:
                errores.append(f"Registro {i}: {str(e)}")
                continue
        
        db.commit()
        
        return {
            "message": f"✅ {registros_procesados} registros guardados en periodo: {periodo_anterior}",
            "registros_procesados": registros_procesados,
            "periodo_utilizado": periodo_anterior,
            "errores": errores if errores else None
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actualizar_aprovechamiento")
async def actualizar_aprovechamiento(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    """
    Actualiza la tabla final usando el periodo anterior al último.
    Lógica de SP integrada directamente aquí.
    """
    try:
        # 1. OBTENER EL PERIODO DINÁMICO (Anterior al último)
        _, periodo_sp = get_periodo_anterior_al_ultimo(db)
        

        # 2. OBTENER RESTO DE VARIABLES (desde sesión)
        unidad_sigla = getattr(sess, 'sigla_unidad_academica', 'ESCOM') or 'ESCOM'
        usuario = getattr(sess, 'usuario', 'sistema') or 'sistema'
        nivel = getattr(sess, 'nombre_nivel', 'Superior') or 'Superior'
        host_sp = get_request_host(request)

        print(f"🔄 EJECUTANDO SP DIRECTAMENTE PARA PERIODO: {periodo_sp}")
        
        # 3. EJECUCIÓN DIRECTA DEL STORED PROCEDURE
        sp_name = "[dbo].[SP_Actualiza_Aprovechamiento_Por_Unidad_Academica]"
        
        db.execute(
            text(f"""
                EXEC {sp_name}
                    @UUnidad_Academica = :unidad_academica,
                    @UUsuario = :usuario,
                    @HHost = :host,
                    @PPeriodo = :periodo,
                    @NNivel = :nivel
            """),
            {
                "unidad_academica": unidad_sigla,
                "usuario": usuario,
                "host": host_sp,
                "periodo": periodo_sp,
                "nivel": nivel
            }
        )
        
        # 4. CONFIRMACIÓN DE CAMBIOS
        db.commit()
        print(f"✅ SP {sp_name} ejecutado y commiteado exitosamente")

        return {
            "mensaje": "Actualización completada exitosamente",
            "periodo_actualizado": periodo_sp,
            "unidad": unidad_sigla
        }
        
    except Exception as e:
        # Importante: Revertir cambios en caso de error en el SP o en la lógica previa
        db.rollback()
        print(f"❌ Error en actualización: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {str(e)}")
        
@router.post("/finalizar_captura_semestre")
async def finalizar_captura_semestre(request: Request, data: Dict[str, Any], sess=Depends(get_current_session), db: Session = Depends(get_db)):
    try:
        # 1. Obtención y limpieza de datos
        unidad_sigla = (getattr(sess, 'sigla_unidad_academica', '') or '').strip()
        usuario = getattr(sess, 'usuario', '') or ''
        host = get_request_host(request)
        programa = data.get("programa", "").strip()
        modalidad = data.get("modalidad", "").strip()
        semestre = data.get("semestre", "").strip()
        _, periodo = get_periodo_activo(db)
        nivel = data.get("nivel", "").strip()

        # 2. IMPRESIÓN DE DEBUG (Copia esto de tu terminal cuando falle)
        print("\n" + "="*50)
        print("🚀 INTENTANDO EJECUTAR SP:")
        debug_query = f"""
        EXEC [dbo].[SP_Actualiza_Aprovechamiento_Por_Semestre_AU]
            @PPeriodo = '{periodo}',
            @UUnidad_Academica = '{unidad_sigla}',
            @MModalidad = '{modalidad}',
            @PPrograma = '{programa}',
            @SSemestre = '{semestre}',
            @UUsuario = '{usuario}',
            @HHost = '{host}',
            @NNivel = '{nivel}'
        """
        print(debug_query)
        print("="*50 + "\n")

        # 3. Ejecución Real
        query = text("""
            EXEC [dbo].[SP_Actualiza_Aprovechamiento_Por_Semestre_AU]
                @PPeriodo = :periodo,
                @UUnidad_Academica = :unidad,
                @MModalidad = :modalidad,
                @PPrograma = :programa, 
                @SSemestre = :semestre,
                @UUsuario = :usuario,
                @HHost = :host,
                @NNivel = :nivel
        """)

        db.execute(query, {
            "periodo": periodo,
            "unidad": unidad_sigla,
            "modalidad": modalidad,
            "programa": programa, 
            "semestre": semestre,
            "usuario": usuario,
            "host": host,
            "nivel": nivel
        })
        
        db.commit()
        return {"status": "success", "message": "Proceso completado."}

    except Exception as e:
        db.rollback()
        print(f"❌ ERROR SQL DETECTADO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Mapa de conversión semestre texto → número
SEMESTRE_A_NUM = {
    'primer': 1, 'primero': 1,
    'segundo': 2,
    'tercer': 3, 'tercero': 3,
    'cuarto': 4,
    'quinto': 5,
    'sexto': 6,
    'séptimo': 7, 'septimo': 7,
    'octavo': 8,
    'noveno': 9,
    'décimo': 10, 'decimo': 10,
    'undécimo': 11, 'undecimo': 11, 'décimo primero': 11,
    'duodécimo': 12, 'duodecimo': 12, 'décimo segundo': 12,
}

def semestre_texto_a_numero(texto):
    """Convierte 'Cuarto' → 4, 'Primero' → 1, etc. Si no reconoce, intenta parsear int."""
    if texto is None:
        return None
    t = str(texto).strip().lower()
    if t in SEMESTRE_A_NUM:
        return SEMESTRE_A_NUM[t]
    # intento directo como número
    try:
        return int(t)
    except ValueError:
        return t  # devuelve tal cual si no se puede convertir


def procesar_datos_aprovechamiento_semestre(rows):
    """
    Misma lógica que procesar_datos_aprovechamiento() pero pivoteando
    por Semestre (columnas) en lugar de Modalidad/Turno.

    Retorna dict con:
      - semestres: lista de números de semestre ordenados
      - tipos_aprovechamiento: lista de tipos únicos
      - programas: lista con estructura de filas por programa
      - total_general_h/m/t
      - total_general_celdas: [{h, m, t}, ...] uno por semestre
    """

    # ── 1. Recolectar valores únicos ─────────────────────────────────────────
    semestres_set = set()
    tipos_aprov_set = []
    programas_set = []

    for r in rows:
        sem_raw = r.get("Semestre")
        sem_num = semestre_texto_a_numero(sem_raw)
        if sem_num is not None:
            semestres_set.add(sem_num)

        apr  = r.get("Aprovechamiento") or ""
        prog = r.get("Nombre_Programa") or ""

        if apr  and apr  not in tipos_aprov_set:  tipos_aprov_set.append(apr)
        if prog and prog not in programas_set:    programas_set.append(prog)

    semestres_ordenados = sorted(semestres_set, key=lambda x: (int(x) if isinstance(x, (int, float)) else 999))

    # ── 2. Sumar alumnos por (programa, semestre_num, aprovechamiento, sexo) ─
    suma = defaultdict(int)
    for r in rows:
        prog    = r.get("Nombre_Programa") or ""
        sem_num = semestre_texto_a_numero(r.get("Semestre"))
        apr     = r.get("Aprovechamiento") or ""
        sexo    = r.get("Sexo") or ""
        val     = r.get("alumnos") or 0
        suma[(prog, sem_num, apr, sexo)] += int(val)

    def hmt(prog, sem, apr):
        h = suma.get((prog, sem, apr, "Hombre"), 0)
        m = suma.get((prog, sem, apr, "Mujer"),  0)
        return h, m, h + m

    # ── 3. Construir estructura por programa ─────────────────────────────────
    estructura_programas = []

    for prog in programas_set:
        filas_aprov = []
        sub_h = sub_m = sub_t = 0

        for apr in tipos_aprov_set:
            fila = {"aprovechamiento": apr, "celdas": [], "total_h": 0, "total_m": 0, "total_t": 0}
            for sem in semestres_ordenados:
                h, m, t = hmt(prog, sem, apr)
                fila["celdas"].append({"h": h, "m": m, "t": t})
                fila["total_h"] += h; fila["total_m"] += m; fila["total_t"] += t

            sub_h += fila["total_h"]; sub_m += fila["total_m"]; sub_t += fila["total_t"]
            filas_aprov.append(fila)

        # subtotales por semestre para fila Subtotal
        sub_celdas = []
        for sem in semestres_ordenados:
            h = m = 0
            for apr in tipos_aprov_set:
                h += suma.get((prog, sem, apr, "Hombre"), 0)
                m += suma.get((prog, sem, apr, "Mujer"),  0)
            sub_celdas.append({"h": h, "m": m, "t": h + m})

        estructura_programas.append({
            "nombre": prog, "filas": filas_aprov,
            "subtotal_h": sub_h, "subtotal_m": sub_m, "subtotal_t": sub_t,
            "subtotales_celdas": sub_celdas,
        })

    # ── 4. Total general ──────────────────────────────────────────────────────
    tg_h = sum(p["subtotal_h"] for p in estructura_programas)
    tg_m = sum(p["subtotal_m"] for p in estructura_programas)

    tg_celdas = []
    for sem in semestres_ordenados:
        h = m = 0
        for prog in programas_set:
            for apr in tipos_aprov_set:
                h += suma.get((prog, sem, apr, "Hombre"), 0)
                m += suma.get((prog, sem, apr, "Mujer"),  0)
        tg_celdas.append({"h": h, "m": m, "t": h + m})

    return {
        "semestres":           semestres_ordenados,
        "tipos_aprovechamiento": tipos_aprov_set,
        "programas":           estructura_programas,
        "total_general_h":     tg_h,
        "total_general_m":     tg_m,
        "total_general_t":     tg_h + tg_m,
        "total_general_celdas": tg_celdas,
    }


def procesar_datos_aprovechamiento(rows):
    modalidades_set = []
    turnos_por_modalidad = defaultdict(list)
    tipos_aprov_set = []
    programas_set = []

    for r in rows:
        mod  = r.get("Modalidad") or ""
        tur  = r.get("Turno") or ""
        apr  = r.get("Aprovechamiento") or ""
        prog = r.get("Nombre_Programa") or ""

        if mod  and mod  not in modalidades_set:   modalidades_set.append(mod)
        if mod and tur and tur not in turnos_por_modalidad[mod]: turnos_por_modalidad[mod].append(tur)
        if apr  and apr  not in tipos_aprov_set:   tipos_aprov_set.append(apr)
        if prog and prog not in programas_set:     programas_set.append(prog)

    suma = defaultdict(int)
    for r in rows:
        prog = r.get("Nombre_Programa") or ""
        mod  = r.get("Modalidad") or ""
        tur  = r.get("Turno") or ""
        apr  = r.get("Aprovechamiento") or ""
        sexo = r.get("Sexo") or ""
        val  = r.get("alumnos") or 0
        suma[(prog, mod, tur, apr, sexo)] += int(val)

    def hmt(prog, mod, tur, apr):
        h = suma.get((prog, mod, tur, apr, "Hombre"), 0)
        m = suma.get((prog, mod, tur, apr, "Mujer"),  0)
        return h, m, h + m

    estructura_programas = []
    for prog in programas_set:
        filas_aprov = []
        sub_h = sub_m = sub_t = 0

        for apr in tipos_aprov_set:
            fila = {"aprovechamiento": apr, "celdas": [], "total_h": 0, "total_m": 0, "total_t": 0}
            for mod in modalidades_set:
                for tur in turnos_por_modalidad[mod]:
                    h, m, t = hmt(prog, mod, tur, apr)
                    fila["celdas"].append({"h": h, "m": m, "t": t})
                    fila["total_h"] += h; fila["total_m"] += m; fila["total_t"] += t
            sub_h += fila["total_h"]; sub_m += fila["total_m"]; sub_t += fila["total_t"]
            filas_aprov.append(fila)

        # subtotales por celda (modalidad x turno)
        sub_celdas = []
        for mod in modalidades_set:
            for tur in turnos_por_modalidad[mod]:
                h = m = 0
                for apr in tipos_aprov_set:
                    h += suma.get((prog, mod, tur, apr, "Hombre"), 0)
                    m += suma.get((prog, mod, tur, apr, "Mujer"),  0)
                sub_celdas.append({"h": h, "m": m, "t": h + m})

        estructura_programas.append({
            "nombre": prog, "filas": filas_aprov,
            "subtotal_h": sub_h, "subtotal_m": sub_m, "subtotal_t": sub_t,
            "subtotales_celdas": sub_celdas,
        })

    # Total general
    tg_h = sum(p["subtotal_h"] for p in estructura_programas)
    tg_m = sum(p["subtotal_m"] for p in estructura_programas)

    tg_celdas = []
    for mod in modalidades_set:
        for tur in turnos_por_modalidad[mod]:
            h = m = 0
            for prog in programas_set:
                for apr in tipos_aprov_set:
                    h += suma.get((prog, mod, tur, apr, "Hombre"), 0)
                    m += suma.get((prog, mod, tur, apr, "Mujer"),  0)
            tg_celdas.append({"h": h, "m": m, "t": h + m})

    return {
        "modalidades": modalidades_set,
        "turnos_por_modalidad": dict(turnos_por_modalidad),
        "tipos_aprovechamiento": tipos_aprov_set,
        "programas": estructura_programas,
        "total_general_h": tg_h,
        "total_general_m": tg_m,
        "total_general_t": tg_h + tg_m,
        "total_general_celdas": tg_celdas,
    }


# ─── Endpoint ──────────────────────────────────────────────────────────────

"""
Endpoint completo con lógica de semáforo para aprovechamiento.

Cadena de validación (Id_Formato == 2):
  Rol 4 (CEGET)         → puede validar si Id_Semaforo == 3  (Validado por Capturista)
  Rol 5 (Titular)       → puede validar si Id_Semaforo == 4  (Validado por CEGET)
  Rol 6 (Analista)      → puede validar si Id_Semaforo == 5  (Validado por Titular)
  Rol 7 (Jefe Depto)    → puede validar si Id_Semaforo == 6  (Validado por Analista)
  Rol 8 (Jefe División) → puede validar si Id_Semaforo == 7  (Validado por Departamento)
  Rol 9 (Director DII)  → puede validar si Id_Semaforo == 8  (Validado por División)
"""

SEMAFORO_REQUERIDO = {
    4: 3,   # CEGET         ← Validado por Capturista
    5: 4,   # Titular       ← Validado por CEGET
    6: 5,   # Analista      ← Validado por Titular
    7: 6,   # Jefe Depto    ← Validado por Analista
    8: 7,   # Jefe División ← Validado por Departamento
    9: 8,   # Director DII  ← Validado por División
}

ID_FORMATO_APROVECHAMIENTO = 2


@router.get("/resumen-dinamico")
async def resumen_aprovechamiento_dinamico_view(
    request: Request,
    periodo: str = "",
    nivel:   str = "",
    unidad:  str = "",
    sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    # ── Sesión ──────────────────────────────────────────────────────────────
    id_rol            = int(getattr(sess, 'id_rol', 0) or 0)
    nombre_rol        = getattr(sess, 'nombre_rol', '') or ''
    nombre_usuario    = getattr(sess, 'nombre_usuario', '') or ''
    apellidoP_usuario = getattr(sess, 'apellidoP_usuario', '') or ''
    apellidoM_usuario = getattr(sess, 'apellidoM_usuario', '') or ''
    nombre_completo   = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    id_usuario_actual = int(getattr(sess, 'id_usuario', 0) or 0)
    if not unidad:
        unidad = (getattr(sess, 'sigla_unidad_academica', '') or '').strip()
    usuario_login = nombre_usuario or "sistema"
    host          = request.client.host

    tabla_datos          = None
    tabla_datos_semestre = None
    error                = None
    nombre_ua            = unidad or "—"
    periodo_activo       = False
    puede_validar        = False
    usuario_ya_valido    = False
    usuario_ya_rechazo   = False
    semaforo_descripcion = ""
    semaforo_color       = ""

    try:
        # ── 1. Periodo activo ────────────────────────────────────────────────
        periodo_obj    = db.query(CatPeriodo).filter(CatPeriodo.Periodo == periodo).first()
        periodo_activo = periodo_obj is not None and periodo_obj.Id_Estatus == 1

        # ── 2. Periodo anterior (para el semáforo) ───────────────────────────
        Periodoant          = get_periodo_anterior_al_ultimo(db)
        Id_Periodo_anterior = Periodoant[0]

        # ── 3. Nivel ─────────────────────────────────────────────────────────
        nivel_obj = db.query(CatNivel).filter(CatNivel.Nivel == nivel).first()
        Id_Nivel  = nivel_obj.Id_Nivel if nivel_obj else None

        # ── 4. Unidad Académica ──────────────────────────────────────────────
        ua_obj = db.query(CatUnidadAcademica).filter(
            CatUnidadAcademica.Sigla == unidad
        ).first()
        Id_Unidad_Academica = ua_obj.Id_Unidad_Academica if ua_obj else None

        # ── 5. Semáforo y estado de validación (roles 4-9) ───────────────────
        if id_rol in SEMAFORO_REQUERIDO and Id_Periodo_anterior and Id_Unidad_Academica and Id_Nivel:

            semaforo_actual = db.query(SemaforoUnidadAcademica).filter(
                SemaforoUnidadAcademica.Id_Periodo          == Id_Periodo_anterior,
                SemaforoUnidadAcademica.Id_Unidad_Academica == Id_Unidad_Academica,
                SemaforoUnidadAcademica.Id_Formato          == ID_FORMATO_APROVECHAMIENTO,
                SemaforoUnidadAcademica.Id_Nivel            == Id_Nivel
            ).first()

            if semaforo_actual:
                # Descripción y color del semáforo
                cat_sem = db.query(CatSemaforo).filter(
                    CatSemaforo.Id_Semaforo == semaforo_actual.Id_Semaforo
                ).first()
                if cat_sem:
                    semaforo_descripcion = cat_sem.Descripcion_Semaforo
                    semaforo_color       = cat_sem.Color_Semaforo

                estado_semaforo    = semaforo_actual.Id_Semaforo
                semaforo_requerido = SEMAFORO_REQUERIDO.get(id_rol)

                print(f"🔍 Verificando estado de validación aprovechamiento...")
                print(f"   id_rol={id_rol}, semaforo_actual={estado_semaforo}, semaforo_requerido={semaforo_requerido}")

                if estado_semaforo == semaforo_requerido and periodo_activo:
                    # Semáforo en el nivel correcto → puede validar
                    puede_validar = True
                    print(f"   ✅ Puede validar")

                elif estado_semaforo >= id_rol:
                    # Semáforo ya avanzó más allá del nivel del rol → ya validó
                    usuario_ya_valido = True
                    puede_validar     = False
                    print(f"   🔒 Ya validó (semáforo={estado_semaforo} >= id_rol={id_rol})")

                else:
                    # Semáforo aún no llegó al nivel del rol → debe esperar
                    puede_validar = False
                    print(f"   ⏳ Debe esperar (semáforo={estado_semaforo} < requerido={semaforo_requerido})")

                # Verificar si el usuario rechazó previamente
                validacion_rechazo = db.query(Validacion).filter(
                    Validacion.Id_Periodo          == Id_Periodo_anterior,
                    Validacion.Id_Usuario          == id_usuario_actual,
                    Validacion.Id_Formato          == ID_FORMATO_APROVECHAMIENTO,
                    Validacion.Validado            == 0   # 0 = rechazo
                ).first()

                if validacion_rechazo and not puede_validar:
                    usuario_ya_rechazo = True
                    puede_validar      = False
                    print(f"   ❌ Ya rechazó previamente")

                print(f"   → puede_validar={puede_validar}, ya_valido={usuario_ya_valido}, ya_rechazo={usuario_ya_rechazo}")

        # ── 6. Ejecutar SP ───────────────────────────────────────────────────
        resultado = db.execute(
            text("""
                SET NOCOUNT ON;
                EXEC [dbo].[SP_Consulta_Aprovechamiento_Unidad_Academica]
                    @UUnidad_Academica = :unidad,
                    @Pperiodo          = :periodo,
                    @NNivel            = :nivel,
                    @UUsuario          = :usuario,
                    @HHost             = :host
            """),
            {
                "unidad":  unidad,
                "periodo": periodo,
                "nivel":   nivel,
                "usuario": usuario_login,
                "host":    host,
            }
        )

        columnas = list(resultado.keys())
        rows_raw = [dict(zip(columnas, row)) for row in resultado.fetchall()]

        if not rows_raw:
            error = "No se encontraron datos para los filtros seleccionados."
        else:
            tabla_datos          = procesar_datos_aprovechamiento(rows_raw)
            tabla_datos_semestre = procesar_datos_aprovechamiento_semestre(rows_raw)

    except Exception as e:
        import traceback
        error = f"Error al generar resumen de aprovechamiento: {e}\n{traceback.format_exc()}"

    return templates.TemplateResponse(
        "aprovechamiento_resumen_dinamico.html",
        {
            "request":               request,
            "periodo":               periodo,
            "nivel":                 nivel,
            "unidad":                unidad,
            "nombre_ua":             nombre_ua,
            "nombre_completo":       nombre_completo,
            "nombre_usuario":        nombre_usuario,
            "nombre_rol":            nombre_rol,
            "id_rol":                id_rol,
            "tabla_datos":           tabla_datos,
            "tabla_datos_semestre":  tabla_datos_semestre,
            "periodo_activo":        periodo_activo,
            "puede_validar":         puede_validar,
            "usuario_ya_valido":     usuario_ya_valido,
            "usuario_ya_rechazo":    usuario_ya_rechazo,
            "semaforo_descripcion":  semaforo_descripcion,
            "semaforo_color":        semaforo_color,
            "error":                 error,
        }
    )

# Mapa rol → semáforo AL QUE AVANZA al validar
SEMAFORO_SIGUIENTE = {
    4: 4,   # CEGET         → Validado por CEGET
    5: 5,   # Titular       → Validado por Titular
    6: 6,   # Analista      → Validado por Analista
    7: 7,   # Jefe Depto    → Validado por Departamento
    8: 8,   # Jefe División → Validado por División
    9: 9,   # Director DII  → Validado por Dirección
}

@router.post("/validar")
async def validar_aprovechamiento(
    request: Request,
    sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    try:
        body           = await request.json()
        periodo        = body.get("periodo", "")
        unidad         = body.get("unidad", "")
        nombre_usuario = getattr(sess, 'usuario', '') or ''
        id_rol         = int(getattr(sess, 'id_rol', 0) or 0)
        host           = request.client.host
        nota           = body.get("nota", "Validación de aprovechamiento")

        # Obtener el semáforo siguiente según el rol
        semaforo_siguiente = SEMAFORO_SIGUIENTE.get(id_rol)
        if not semaforo_siguiente:
            return {"success": False, "error": "Rol no autorizado para validar."}

        db.execute(
            text("""
                SET NOCOUNT ON;
                EXEC [dbo].[SP_Valida_Aprovechamniento]
                    @PPeriodo          = :periodo,
                    @UUnidad_Academica = :unidad,
                    @uusuario          = :usuario,
                    @HHost             = :host,
                    @NNota             = :nota,
                    @semaforo          = :semaforo
            """),
            {
                "periodo":  periodo,
                "unidad":   unidad,
                "usuario":  nombre_usuario,
                "host":     host,
                "nota":     nota,
                "semaforo": semaforo_siguiente,
            }
        )
        db.commit()

        return {"success": True, "mensaje": f"Aprovechamiento validado correctamente para {unidad} - {periodo}."}

    except Exception as e:
        import traceback
        db.rollback()
        return {"success": False, "error": f"Error al validar: {e}\n{traceback.format_exc()}"}


SEMAFORO_RECHAZO = {
    4: 10,  # CEGET         → Regresado por CEGET
    5: 11,  # Titular       → Regresado por Titular
    6: 12,  # Analista      → Regresado por Analista
    7: 13,  # Jefe Depto    → Regresado por Departamento
    8: 14,  # Jefe División → Regresado por División
    9: 15,  # Director DII  → Regresado por Dirección
}

@router.post("/rechazar")
async def rechazar_aprovechamiento(
    request: Request,
    sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    try:
        body           = await request.json()
        periodo        = body.get("periodo", "")
        unidad         = body.get("unidad", "")
        motivo         = body.get("motivo", "")
        nombre_usuario = getattr(sess, 'usuario', '') or ''
        id_rol         = int(getattr(sess, 'id_rol', 0) or 0)
        host           = request.client.host

        if not motivo or len(motivo.strip()) < 10:
            return {"success": False, "error": "El motivo del rechazo debe tener al menos 10 caracteres."}

        semaforo_rechazo = SEMAFORO_RECHAZO.get(id_rol)
        if not semaforo_rechazo:
            return {"success": False, "error": "Rol no autorizado para rechazar."}

        db.execute(
            text("""
                SET NOCOUNT ON;
                EXEC [dbo].[SP_Rechaza_Aprovechamniento]
                    @PPeriodo          = :periodo,
                    @UUnidad_Academica = :unidad,
                    @uusuario          = :usuario,
                    @HHost             = :host,
                    @NNota             = :nota,
                    @semaforo          = :semaforo
            """),
            {
                "periodo":  periodo,
                "unidad":   unidad,
                "usuario":  nombre_usuario,
                "host":     host,
                "nota":     motivo,
                "semaforo": semaforo_rechazo,
            }
        )
        db.commit()

        return {"success": True, "mensaje": f"Aprovechamiento rechazado correctamente para {unidad} - {periodo}."}

    except Exception as e:
        import traceback
        db.rollback()
        return {"success": False, "error": f"Error al rechazar: {e}\n{traceback.format_exc()}"}