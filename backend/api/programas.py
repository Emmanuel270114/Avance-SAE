from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from backend.core.templates import templates
from backend.database.connection import get_db
from sqlalchemy.orm import Session
from sqlalchemy import join
from backend.database.models.CatProgramas import CatProgramas
from backend.database.models.ProgramaModalidad import ProgramaModalidad
from backend.database.models.UnidadProgramaModalidad import CatUnidadProgramaModalidad
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.database.models.CatModalidad import CatModalidad
from backend.database.models.CatNivel import CatNivel

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def programas_view(request: Request, db: Session = Depends(get_db)):
    # Obtener datos del usuario logueado desde las cookies
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 1))
    id_rol = int(request.cookies.get("id_rol", 2))
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    
    # Verificar si es super admin
    es_super_admin = (nombre_usuario.strip().lower() == 'admin' and
                     apellidoP_usuario.strip().lower() == 'admin' and
                     apellidoM_usuario.strip().lower() == 'admin')
    
    programas_por_ua = {}
    todas_uas = []
    if es_super_admin:
        todas_uas = db.query(CatUnidadAcademica).all()
        # No cargar programas aquí, solo pasar la lista de UAs
    else:
        # Usuarios normales solo ven programas de su UA
        unidad_academica = db.query(CatUnidadAcademica).filter_by(Id_Unidad_Academica=id_unidad_academica).first()
        upms = db.query(CatUnidadProgramaModalidad).filter_by(Id_Unidad_Academica=id_unidad_academica).all()
        
        programas_info = []
        for upm in upms:
            pm = db.query(ProgramaModalidad).filter_by(Id_Modalidad_Programa=upm.Id_Modalidad_Programa).first()
            if not pm:
                continue
                
            programa = db.query(CatProgramas).filter_by(Id_Programa=pm.Id_Programa).first()
            if not programa:
                continue
                
            modalidad = db.query(CatModalidad).filter_by(Id_Modalidad=pm.Id_Modalidad).first()
            nivel = db.query(CatNivel).filter_by(Id_Nivel=programa.Id_Nivel).first()
            
            programas_info.append({
                'nombre_programa': programa.Nombre_Programa,
                'modalidad': modalidad.Modalidad if modalidad else 'Sin modalidad',
                'nivel': nivel.Nivel if nivel else 'Sin nivel'
            })
        
        if unidad_academica and programas_info:
            ua_key = f"{unidad_academica.Sigla} - {unidad_academica.Nombre}"
            programas_por_ua[ua_key] = programas_info

    return templates.TemplateResponse(
        "programas.html",
        {
            "request": request,
            "programas_por_ua": programas_por_ua,
            "es_super_admin": es_super_admin,
            "todas_uas": todas_uas
        }
    )


# Endpoint para obtener programas de una UA específica (solo superadmin)
@router.get("/por-ua/{id_ua}", response_class=JSONResponse)
async def programas_por_ua(id_ua: int, request: Request, db: Session = Depends(get_db)):
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    es_super_admin = (nombre_usuario.strip().lower() == 'admin' and
                     apellidoP_usuario.strip().lower() == 'admin' and
                     apellidoM_usuario.strip().lower() == 'admin')
    if not es_super_admin:
        return JSONResponse(status_code=403, content={"error": "No autorizado"})

    unidad_academica = db.query(CatUnidadAcademica).filter_by(Id_Unidad_Academica=id_ua).first()
    if not unidad_academica:
        return JSONResponse(status_code=404, content={"error": "Unidad Académica no encontrada"})

    upms = db.query(CatUnidadProgramaModalidad).filter_by(Id_Unidad_Academica=id_ua).all()
    programas_info = []
    for upm in upms:
        pm = db.query(ProgramaModalidad).filter_by(Id_Modalidad_Programa=upm.Id_Modalidad_Programa).first()
        if not pm:
            continue
        programa = db.query(CatProgramas).filter_by(Id_Programa=pm.Id_Programa).first()
        if not programa:
            continue
        modalidad = db.query(CatModalidad).filter_by(Id_Modalidad=pm.Id_Modalidad).first()
        nivel = db.query(CatNivel).filter_by(Id_Nivel=programa.Id_Nivel).first()
        programas_info.append({
            'nombre_programa': programa.Nombre_Programa,
            'modalidad': modalidad.Modalidad if modalidad else 'Sin modalidad',
            'nivel': nivel.Nivel if nivel else 'Sin nivel'
        })
    return {"programas": programas_info, "ua": f"{unidad_academica.Sigla} - {unidad_academica.Nombre}"}
