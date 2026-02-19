from fastapi import APIRouter, Request, Depends, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import JSONResponse


from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.periodo_service import get_ultimo_periodo, get_periodo_activo

router = APIRouter()
HHost: str = "Test"

@router.get("/semaforo", response_class=HTMLResponse)
def semaforo_view(
    request: Request,
    db: Session = Depends(get_db)
):
    
    UUsuario = request.cookies.get("nombre_usuario", "")
    Rol = request.cookies.get("nombre_rol","")
    
    # Obtener periodo dinámico (priorizar activo)
    _, PPeriodo = get_periodo_activo(db) or get_ultimo_periodo(db)
    if not PPeriodo:
        PPeriodo = ""  # Valor vacío si no hay periodo

    try:
        # Ejecutar el Stored Procedure con parámetros nombrados
        query = text("""
            EXEC dbo.SP_Consulta_Catalogo_Semaforo
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
        print("Error al ejecutar SP_Consulta_Catalogo_Semaforo:", e)
        data = []

    # Renderizar la plantilla HTML con los resultados
    return templates.TemplateResponse(
        "catalogos/semaforo.html",
        {
            "request": request,
            "semaforo": data,
            "rol": Rol
        }
    )



@router.post("/semaforo/registrar")
async def registrar_semaforo(data: dict):
    print(data)
    return JSONResponse(
            content={"mensaje": "Registrado correctamente"},
            status_code=200
        )

router.put("/semaforo/actualizar")
async def actualizar_semaforo(data: dict):
    print(data)
    return JSONResponse(
            content={"mensaje": "Actualizado correctamente"},
            status_code=200
        )
