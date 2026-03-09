from os import error, nice
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.api import unidad_academica
from backend.database.connection import get_db
from backend.core.templates import templates
from backend.schemas import Nivel
from backend.services.titulados_service import obtener_titulados
from backend.services.periodo_service import get_ultimo_periodo
from backend.database.models.CatBoleta import CatBoleta as Boleta

router = APIRouter()

@router.get("/consulta", response_class=HTMLResponse)

async def consulta_titulados(
    request: Request,
    db: Session = Depends(get_db)
):
    
    contexto = {}
    filas = []
    
    # Identificar la vista para usuarios (Quitar los default ya que conecte a la base)
    id_rol = int(request.cookies.get("id_rol",0))
    nombre_rol = request.cookies.get("nombre_rol", "Capturista")
    nombre = request.cookies.get("nombre_usuario", "Prueba")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "123")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "456")
    nombre_usuario = " ".join(filter(None, [nombre, apellidoP_usuario, apellidoM_usuario]))
    
    unidad_academica = request.cookies.get("unidad_academica", "unidad_prueba")
    sigla_unidad_academica = request.cookies.get("sigla_unidad_academica", "UAP")
    nombre_nivel = request.cookies.get("nombre_nivel", "Nivel de Prueba")
    nivel_acceso = request.cookies.get("id_nivel")
    usuario = request.cookies.get("usuario", "usuario_prueba")

    host = "Test"

    try:
        periodo_id, periodo_literal = get_ultimo_periodo(db)
        if not periodo_id or not periodo_literal:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_message": "No hay un periodo activo configurado en el sistema.",
                "redirect_url": "/mod_principal/"
            })
        
        periodo_default_literal = periodo_literal
        print(f" Periodo por defecto: {periodo_default_literal}")
    except Exception as e:
        print(f" Error al obtener periodo: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error_message": f"Error al cargar el periodo: {str(e)}",
            "redirect_url": "/mod_principal/"
        })

    roles_permitidos = [1, 3, 4, 5, 6, 7, 8, 9]  #1=Admin, 3=Capturista, 4-9=Roles de validación/rechazo
    if id_rol not in roles_permitidos:
        if id_rol != 0:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_message": f"Acceso denegado: Su rol ({nombre_rol}) no tiene permisos para acceder a esta funcionalidad.",
                "redirect_url": "/mod_principal/"
            })
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_message": "Acceso denegado: No se ha identificado un rol válido. Por favor, inicie sesión.",
                "redirect_url": "/login/"
            })
    

    es_capturista = (id_rol == 3)
    es_validador = (id_rol in [4, 5, 6, 7, 8, 9])  
    es_rol_director = (id_rol in [4, 5])  
    es_rol_superior = (id_rol in [6, 7, 8, 9])  
    modo_vista = "captura" if es_capturista else "validacion"




    try:
        
        print(f"Obteniendo titulados para UA: {sigla_unidad_academica}, Periodo: {periodo_default_literal}, Nivel: {nombre_nivel}, Usuario: {usuario}")
        contexto, filas = obtener_titulados(
            db=db,
            unidad_academica=sigla_unidad_academica,
            periodo=periodo_default_literal,
            nivel=nombre_nivel,
            usuario=usuario,
            host=host
        )

        boleta = contexto.get("Boleta", "N/A")
        boletas = list(range(boleta + 1, boleta - 11, -1)) if boleta else []
        print(f"Boletas obtenida: {boletas}")

        
    
    

    except ValueError as ve:
        return templates.TemplateResponse("titulados_consulta.html", {"request": request, "error": str(ve)})
    except Exception as e:
        return templates.TemplateResponse("titulados_consulta.html", {"request": request, "error": f"Error al obtener datos: {e}"})
    
   
   # print(f"Contexto final: {contexto}")                
    return templates.TemplateResponse(
            "titulados_consulta.html", 
            {"request": request,
             "nombre_usuario": nombre_usuario,
             "periodo_default_literal": periodo_default_literal,
             "unidad_academica" : unidad_academica,
             "nombre_rol": nombre_rol,
             "nivel_acceso" : nivel_acceso,
             "contexto": contexto,
             "boletas": boletas,
             "filas": filas,
             "acceso_restringido" : False}
             )
