from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database.connection import get_db
from backend.core.templates import templates

router = APIRouter()


@router.get("/modulos", response_class=HTMLResponse)
def modulos_view(
    request: Request,
    db: Session = Depends(get_db)
):

    Rol = str(request.cookies.get("nombre_rol",""))

    try:
        # Ejecutar el Stored Procedure con parámetros nombrados
        query = text("""
            EXEC dbo.SP_Consulta_Catalogo_Modulos
        """)
        resultado = db.execute(query,)

        # Convertir el resultado a lista de diccionarios
        data = [dict(row) for row in resultado.mappings().all()]
        print(data)

    except Exception as e:
        print("Error al ejecutar SP_Consulta_Catalogo_Modulos:", e)
        data = []

    # Renderizar la plantilla HTML con los resultados
    return templates.TemplateResponse(
        "catalogos/modulos.html",
        {
            "request": request,
            "modulos": data,
            "rol": Rol
        }
    )
