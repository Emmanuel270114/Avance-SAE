from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.periodo_service import get_ultimo_periodo, get_periodo_activo

router = APIRouter()


@router.get("/estatus", response_class=HTMLResponse)
def estatus_view(
    request: Request,
    HHost: str = "Test",
    db: Session = Depends(get_db)
):
    
    
    UUsuario = str(request.cookies.get("nombre_usuario", ""))
    Rol = str(request.cookies.get("nombre_rol",""))
    
    # Obtener periodo dinámico (priorizar activo)
    _, PPeriodo = get_periodo_activo(db) or get_ultimo_periodo(db)
    if not PPeriodo:
        PPeriodo = ""  # Valor vacío si no hay periodo






    """
    Vista para consultar los domicilios mediante un Stored Procedure.
    """

    try:
        # Ejecutar el Stored Procedure con parámetros nombrados
        query = text("""
            EXEC dbo.SP_Consulta_Catalogo_Estatus
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
        print("Error al ejecutar SP_Consulta_Catalogo_Estatus:", e)
        data = []

    # Renderizar la plantilla HTML con los resultados
    return templates.TemplateResponse(
        "catalogos/estatus.html",
        {
            "request": request,
            "estatus": data,
            "rol": Rol
        }
    )
