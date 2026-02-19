from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.unidad_services import get_all_units
from backend.services.usuario_service import register_usuario
from backend.services.nivel_service import get_all_niveles, get_niveles_by_unidad_academica
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse
from backend.core.templates import templates
from backend.database.models.Usuario import Usuario


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def registro_view(request: Request, db: Session = Depends(get_db)):
    try:
        unidades_academicas = get_all_units(db)
        niveles = get_all_niveles(db)
        
        # Intentar leer el rol del usuario logueado desde cookie
        id_rol_cookie = request.cookies.get("id_rol")
        if id_rol_cookie and str(id_rol_cookie).isdigit():
            roles = get_roles_for_user_group(db, int(id_rol_cookie))
        else:
            # Fallback: mostrar todos los roles si no hay sesión
            roles = get_all_roles(db)
        
        # FILTRAR ROLES 6-9 QUE YA TIENEN USUARIO ASIGNADO (solo un usuario por rol superior)
        roles_superiores_con_usuario = set()
        for rol_id in [6, 7, 8, 9]:
            usuario_existente = db.query(Usuario).filter(
                Usuario.Id_Rol == rol_id,
                Usuario.Id_Estatus == 1  # Solo usuarios activos
            ).first()
            if usuario_existente:
                roles_superiores_con_usuario.add(rol_id)
                print(f"⚠️ Rol {rol_id} ya tiene usuario asignado: {usuario_existente.Nombre} {usuario_existente.Paterno}")
        
        # Filtrar roles que ya están ocupados
        roles_disponibles = [
            rol for rol in roles 
            if rol.Id_Rol not in roles_superiores_con_usuario
        ]
        
        print(f"📋 Roles filtrados: {len(roles)} total, {len(roles_disponibles)} disponibles")
        print(f"🔒 Roles superiores ocupados: {roles_superiores_con_usuario}")
        
        return templates.TemplateResponse(
            "registro.html",
            {"request": request, "unidades_academicas": unidades_academicas, "roles": roles_disponibles, "niveles": niveles},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/", response_model=UsuarioResponse)
async def register_user_endpoint(user: UsuarioCreate, db: Session = Depends(get_db)):
    try:
        # VALIDACIÓN: Roles 6-9 solo pueden tener un usuario activo
        if user.Id_Rol in [6, 7, 8, 9]:
            usuario_existente = db.query(Usuario).filter(
                Usuario.Id_Rol == user.Id_Rol,
                Usuario.Id_Estatus == 1  # Solo usuarios activos
            ).first()
            
            if usuario_existente:
                nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                rol_nombre = db.query(Usuario).join(
                    Usuario.rol  # Assuming there's a relationship defined
                ).filter(Usuario.Id_Usuario == usuario_existente.Id_Usuario).first()
                
                raise ValueError(
                    f"El rol superior seleccionado ya tiene un usuario asignado: {nombre_existente}. "
                    f"Los roles de nivel superior (6-9) solo pueden ser asignados a un usuario a la vez."
                )
        
        return register_usuario(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# Endpoint para obtener niveles por UA
@router.get("/niveles-por-ua/{id_unidad_academica}", response_class=JSONResponse)
async def niveles_por_ua(id_unidad_academica: int, db: Session = Depends(get_db)):
    try:
        niveles = get_niveles_by_unidad_academica(db, id_unidad_academica)
        return [n.model_dump() for n in niveles]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})