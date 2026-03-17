from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from backend.core.templates import templates
from backend.core.auth import get_current_session

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def mod_principal_view(request: Request, sess=Depends(get_current_session)):
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    return templates.TemplateResponse("Mod_Principal.html", {"request": request, "nombre_usuario": nombre_completo})


@router.get("/dashboard_sae", response_class=HTMLResponse)
def dashboard_sae_view(request: Request, sess=Depends(get_current_session)):
    """Página del dashboard SAE embebido de Power BI"""
    return templates.TemplateResponse("dashboard_sae.html", {"request": request})


@router.get("/dashboard_matricula", response_class=HTMLResponse)
def dashboard_matricula_view(request: Request, sess=Depends(get_current_session)):
    """Página del dashboard de Matrícula embebido de Power BI"""
    return templates.TemplateResponse("dashboard_matricula.html", {"request": request})

