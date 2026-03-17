from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db
from backend.core.templates import templates
from backend.core.auth import get_current_session
from backend.services.periodo_service import get_ultimo_periodo, get_periodo_activo

router = APIRouter()

HHost: str = "Test"

@router.get("/periodos", response_class=HTMLResponse)
def domicilios_view(
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    
    UUsuario = str(sess.nombre_usuario)
    Rol = str(sess.nombre_rol)

    # Obtener periodo dinámico (priorizar activo)
    _, PPeriodo = get_periodo_activo(db) or get_ultimo_periodo(db)
    if not PPeriodo:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": "No hay periodos configurados en el sistema.",
            "redirect_url": "/mod_principal/"
        })
    
    try:
        # Ejecutar el Stored Procedure con parámetros nombrados
        query = text("""
            EXEC dbo.SP_Consulta_Catalogo_Periodos
                @UUsuario = :UUsuario,
                @HHost = :HHost,
                @PPeriodo = :PPeriodo
        """)
        resultado = db.execute(query, {
            "UUsuario": UUsuario,
            "HHost": HHost,
            "PPeriodo": PPeriodo
        })

        # Convertir el resultado a lista de diccionarios
        data = [dict(row) for row in resultado.mappings().all()]
        print(data)

    except Exception as e:
        print("Error al ejecutar SP_Consulta_Catalogo_Periodos:", e)
        data = []

    # Renderizar la plantilla HTML con los resultados
    return templates.TemplateResponse(
        "catalogos/periodos.html",
        {
            "request": request,
            "periodos": data,
            "rol": Rol
        }
    )

@router.post("/nuevo_periodo")  
def nuevo_periodo(request: Request, data: dict, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    # Obtener información del usuario desde las cookies
    UUsuario = str(sess.nombre_usuario)
    
    print(f"Creando periodo: {data['periodo']} por usuario: {UUsuario}")
    print(f"Fecha inicial: {data.get('fecha_inicial')}, Fecha final: {data.get('fecha_final')}")
    
    try:
        # PASO 1: Ejecutar el SP para crear el nuevo periodo
        print("📝 Creando nuevo periodo...")
        query = text("""
            EXEC dbo.SP_Inicia_periodo
                @PPeriodo = :PPeriodo,
                @FFecha_Inicial = :FFecha_Inicial,
                @FFecha_Final = :FFecha_Final,
                @HHost = :HHost,
                @UUsuario = :UUsuario
        """)
        
        db.execute(query, {
            "PPeriodo": data["periodo"],
            "FFecha_Inicial": data["fecha_inicial"],
            "FFecha_Final": data["fecha_final"],
            "HHost": HHost,
            "UUsuario": UUsuario
        })
        
        db.commit()
        print("✅ Periodo creado exitosamente.")
        return {"status": "success", "message": "Periodo creado exitosamente."}
    except Exception as e:
        print("Error al crear nuevo periodo:", e)
        return {"status": "error", "message": "Error al crear nuevo periodo."}
