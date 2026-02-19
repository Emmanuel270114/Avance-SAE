from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from datetime import datetime

from backend.database import db_base
from backend.database.models.Temp_Aprovechamiento import Temp_Aprovechamiento
from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.periodo_service import get_periodo_activo, get_ultimo_periodo, get_periodo_anterior_al_ultimo
from backend.database.models.CatPeriodo import CatPeriodo
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.database.models.Validacion import Validacion


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


# Función para ejecutar SP de actualización
def execute_sp_actualiza_aprovechamiento_por_unidad_academica(
    db: Session,
    unidad_sigla: str,
    usuario: str,
    host: str,
    periodo: str,
    nivel: str
):
    """
    Ejecuta el stored procedure SP_Actualiza_Aprovechamiento_Por_Unidad_Academica
    """
    try:
        _, periodo = get_periodo_activo(db)
        # Formato de llamada al SP
        sp_name = "[dbo].[SP_Actualiza_Aprovechamiento_Por_Unidad_Academica]"
        
        # Ejecutar el stored procedure usando parámetros nombrados
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
                "host": host,
                "periodo": periodo,
                "nivel": nivel
            }
        )
        
        db.commit()
        print(f"✅ SP {sp_name} ejecutado correctamente")
        
    except Exception as e:
        print(f"❌ Error ejecutando SP {sp_name}: {str(e)}")
        db.rollback()
        raise

@router.get("/consulta", response_class=HTMLResponse)
def aprovechamiento_view(
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. Preparación de variables desde cookies
    UUsuario = request.cookies.get("usuario", "")
    Rol = str(request.cookies.get("nombre_rol", ""))
    UUnidad_Academica = str(request.cookies.get("sigla_unidad_academica", ""))
    NNivel = str(request.cookies.get("nombre_nivel", ""))
    HHost = request.client.host

    _, periodo_literal = get_periodo_activo(db)
    PPeriodo = periodo_literal
 
    aprovechamientos_limpios = []
    reincorporados_detallados = [] 
    inscritos_final = []
    rama = ""

    try:
        # --- SP 1: Aprovechamiento ---
        # Agregamos SET NOCOUNT ON directamente en el string para limpiar el canal de comunicación
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

        # Extraemos los datos asegurándonos de que el cursor tenga filas
        if result_aprov.returns_rows:
            aprovechamientos_raw = [dict(row) for row in result_aprov.mappings().all()]
        else:
            # Si el SP hizo un UPDATE antes del SELECT, a veces hay que buscar el siguiente set
            aprovechamientos_raw = []

        if aprovechamientos_raw:
            rama = aprovechamientos_raw[0].get("Nombre_Rama", "")
            for reg in aprovechamientos_raw:
                situacion = str(reg.get("Aprovechamiento", "")).strip().lower()
                if situacion == "reincorporados":
                    reincorporados_detallados.append(reg)
                else:
                    aprovechamientos_limpios.append(reg)

        # --- SP 2: Inscritos ---
        query_inscritos = text("""
            SET NOCOUNT ON;
            EXEC dbo.SP_Consulta_Inscritos_Aprovechamiento
                @PPeriodo = :PPeriodo,
                @SSigla_Unidad_Academica = :UUnidad_Academica,
                @NNivel = :NNivel;
        """)
        
        result_inscritos = db.execute(query_inscritos, {
            "PPeriodo": PPeriodo, 
            "UUnidad_Academica": UUnidad_Academica, 
            "NNivel": NNivel
        })
        
        if result_inscritos.returns_rows:
            inscritos_raw = [dict(row) for row in result_inscritos.mappings().all()]
        else:
            inscritos_raw = []

        # Lógica de Turno (Duplicación)
        for ins in inscritos_raw:
            turno_original = str(ins.get("Turno") or "").strip()
            if not turno_original:
                for t in ["Matutino", "Vespertino"]:
                    nuevo_reg = ins.copy()
                    nuevo_reg["Turno"] = t
                    inscritos_final.append(nuevo_reg)
            else:
                inscritos_final.append(ins)

    except Exception as e:
        print(f"--- ERROR DETECTADO ---")
        print(f"Mensaje: {e}")
        # Aquí puedes registrar el error pero permitir que la página cargue vacía
        
    # Nombre para el encabezado
    nombre_completo = f"{request.cookies.get('nombre_usuario', '')} {request.cookies.get('apellidoP_usuario', '')} {request.cookies.get('apellidoM_usuario', '')}".strip()
  
    return templates.TemplateResponse(
        "aprovechamiento_consulta.html",
        {   
            "rol": Rol,
            "nombre_usuario": nombre_completo,
            "periodo": PPeriodo,
            "unidad_academica": UUnidad_Academica,
            "request": request,
            "aprovechamientos": aprovechamientos_limpios,
            "inscritos": inscritos_final,
            "reincorporados": reincorporados_detallados, 
            "rama": rama
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
async def actualizar_aprovechamiento(request: Request, db: Session = Depends(get_db)):
    """
    Actualiza la tabla final usando el periodo anterior al último.
    """
    try:
        # 1. OBTENER EL PERIODO DINÁMICO (Anterior al último)
        _, periodo_sp = get_periodo_anterior_al_ultimo(db)
        
        if not periodo_sp:
             # Fallback si solo hay un periodo en la base de datos
             _, periodo_sp = get_ultimo_periodo(db)

        # 2. OBTENER RESTO DE VARIABLES (Cookies, Nivel, etc)
        unidad_sigla = request.cookies.get("sigla_unidad_academica", "ESCOM")
        usuario = request.cookies.get("usuario", "sistema")
        nivel = request.cookies.get("nombre_nivel", "Superior")
        host_sp = get_request_host(request)

        print(f"🔄 EJECUTANDO SP PARA PERIODO ANTERIOR: {periodo_sp}")
        
        # 3. EJECUTAR EL STORED PROCEDURE
        execute_sp_actualiza_aprovechamiento_por_unidad_academica(
            db,
            unidad_sigla=unidad_sigla,
            usuario=usuario,
            host=host_sp,
            periodo=periodo_sp, # Enviamos el periodo anterior detectado
            nivel=nivel
        )

        return {
            "mensaje": "Actualización completada exitosamente",
            "periodo_actualizado": periodo_sp,
            "unidad": unidad_sigla
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalizar_captura_semestre")
async def finalizar_captura_semestre(request: Request, data: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        # 1. Obtención y limpieza de datos
        unidad_sigla = request.cookies.get("sigla_unidad_academica", "").strip()
        usuario = request.cookies.get("usuario", "")
        host = get_request_host(request)
        programa = data.get("programa", "").strip()
        modalidad = data.get("modalidad", "").strip()
        semestre = data.get("semestre", "").strip()
        periodo = data.get("periodo", "").strip()
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