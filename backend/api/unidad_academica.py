from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from backend.core.templates import templates
from backend.database.connection import get_db
from sqlalchemy.orm import Session
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.database.models.CatDomicilios import CatDomicilios
from backend.database.models.Temporal_Entidades_Municipios import temporal_Entidades_Municipios

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def unidad_academica_view(request: Request, db: Session = Depends(get_db)):
    # Obtener ID de UA desde cookies del usuario logueado
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 1))
    
    # Obtener información de la UA
    unidad_academica = db.query(CatUnidadAcademica).filter_by(Id_Unidad_Academica=id_unidad_academica).first()
    
    # Obtener domicilio de la UA
    domicilio = db.query(CatDomicilios).filter_by(Id_Unidad_Academica=id_unidad_academica).first()
    
    # Obtener información de entidad/municipio si existe el domicilio
    entidad_municipio = None
    if domicilio:
        entidad_municipio = db.query(temporal_Entidades_Municipios).filter_by(
            IdEntidadMunicipio=str(domicilio.Id_Entidad_Municipio)
        ).first()
        
    # Renderizar la plantilla con los datos obtenidos
    return templates.TemplateResponse(
        "unidad_academica.html",
        {
            "request": request,
            "unidad_academica": unidad_academica,
            "domicilio": domicilio,
            "entidad_municipio": entidad_municipio
        }
    )