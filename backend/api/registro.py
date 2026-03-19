from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.unidad_services import get_all_units
from backend.services.usuario_service import register_usuario
from backend.services.usuario_service import is_super_admin
from backend.services.nivel_service import get_all_niveles, get_niveles_by_unidad_academica
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse
from backend.core.templates import templates
from backend.core.auth import get_current_session
from backend.database.models.Usuario import Usuario


# Reglas de asignacion de roles (alineadas con vista de usuarios)
PERMISOS_CREACION_ROLES = {
    1: [2, 3, 4, 5, 6, 7, 8, 9],
    4: [3, 5],
    5: [3, 4],
    7: [4, 5, 6, 8, 9],
    8: [4, 6, 7, 9],
    9: [3, 4, 5, 6, 7, 8],
}

ROLES_SUPERIORES_UNICOS = {6, 7, 8, 9}

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def registro_view(request: Request, sess=Depends(get_current_session), db: Session = Depends(get_db)):
    try:
        unidades_academicas = get_all_units(db)
        niveles = get_all_niveles(db)
        id_rol = int(sess.id_rol)

        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
        
        # Filtrar roles disponibles segun permisos del rol logueado
        try:
            roles = get_roles_for_user_group(db, id_rol)
        except Exception:
            roles = get_all_roles(db)
        
        if es_super_admin:
            roles_disponibles = [rol for rol in roles if rol.Id_Rol != id_rol]
        elif id_rol in PERMISOS_CREACION_ROLES:
            roles_permitidos = PERMISOS_CREACION_ROLES[id_rol]
            roles_disponibles = [rol for rol in roles if rol.Id_Rol in roles_permitidos]
        else:
            roles_disponibles = []

        # Ocultar roles superiores (6-9) ya ocupados en el alta por defecto.
        roles_superiores_ocupados = {
            int(r[0])
            for r in db.query(Usuario.Id_Rol)
            .filter(Usuario.Id_Rol.in_(ROLES_SUPERIORES_UNICOS), Usuario.Id_Estatus == 1)
            .distinct()
            .all()
        }
        roles_disponibles = [
            rol for rol in roles_disponibles if rol.Id_Rol not in roles_superiores_ocupados
        ]
        
        return templates.TemplateResponse(
            "registro.html",
            {"request": request, "unidades_academicas": unidades_academicas, "roles": roles_disponibles, "niveles": niveles},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@router.post("/", response_model=UsuarioResponse)
async def register_user_endpoint(
    user: UsuarioCreate,
    sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    try:
        id_rol_registrador = int(sess.id_rol)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)

        if not es_super_admin:
            if id_rol_registrador not in PERMISOS_CREACION_ROLES:
                raise ValueError("No tienes permisos para crear usuarios.")

            roles_permitidos = PERMISOS_CREACION_ROLES[id_rol_registrador]
            if user.Id_Rol not in roles_permitidos:
                raise ValueError("No tienes permisos para crear un usuario con este rol.")

        # Roles superiores 6-9: solo uno activo por rol.
        if user.Id_Rol in ROLES_SUPERIORES_UNICOS:
            usuario_existente = db.query(Usuario).filter(
                Usuario.Id_Rol == user.Id_Rol,
                Usuario.Id_Estatus == 1,
            ).first()
            if usuario_existente:
                nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                rol_nombres = {6: "Analista", 7: "Jefe/a de División", 8: "Titular", 9: "Administrador General"}
                raise ValueError(
                    f"Ya existe un {rol_nombres.get(user.Id_Rol, 'usuario')} activo: {nombre_existente}"
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
