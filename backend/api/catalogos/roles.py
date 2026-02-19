from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db
from backend.core.templates import templates
from backend.services.periodo_service import get_ultimo_periodo, get_periodo_activo

router = APIRouter()


@router.get("/roles", response_class=HTMLResponse)
def roles_view(
    request: Request,
    HHost: str = "Test",
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
            EXEC dbo.SP_Consulta_Catalogo_Roles
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
        print("Error al ejecutar SP_Consulta_Catalogo_Roles:", e)
        data = []

    # Renderizar la plantilla HTML con los resultados
    return templates.TemplateResponse(
        "catalogos/roles.html",
        {
            "request": request,
            "roles": data,
            "rol": Rol
        }
    )
