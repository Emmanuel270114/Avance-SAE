from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from backend.core.templates import templates
from backend.core.auth import get_current_session
from backend.database.connection import get_db
from backend.database.models.Usuario import Usuario
from backend.services.usuario_service import (
    is_super_admin,
    has_admin_permissions,
    get_unidad_academica_nombre,
)
from backend.services.usuario_sp_service import (
    get_formatos_activos,
    get_usuarios_vista_sp,
    registrar_usuario_sp,
    modificar_usuario_sp,
    baja_usuario_sp,
)
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.unidad_services import get_all_units
from backend.services.nivel_service import get_all_niveles
from backend.services.periodo_service import get_ultimo_periodo
from backend.schemas.Usuario import UsuarioCreate
from sqlalchemy.orm import Session
from backend.utils.request import get_request_host

router = APIRouter()

# Definir qué roles puede crear cada rol
PERMISOS_CREACION_ROLES = {
    1: [2, 3, 4, 5, 6, 7, 8, 9],  # Rol 1 puede crear todos menos él mismo
    4: [3, 5],  # Rol 4 puede crear roles 3 y 5
    5: [3, 4],  # Rol 5 puede crear roles 3 y 4
    7: [4, 6, 8, 9],  # Rol 7 puede crear roles 6, 8, 9
    8: [4, 6, 7, 9],  # Rol 8 puede crear roles 6, 7, 9
    9: [3, 4, 5, 6, 7, 8],  # Rol 9 puede crear todos menos él mismo
}

ROLES_SIN_FORMATO = {6, 7, 8, 9}
ROLES_SUPERIORES_UNICOS = {6, 7, 8, 9}


def _usuario_activo_por_rol(db: Session, id_rol: int, excluir_id_usuario: int | None = None) -> Usuario | None:
    q = db.query(Usuario).filter(
        Usuario.Id_Rol == id_rol,
        Usuario.Id_Estatus == 1,
    )
    if excluir_id_usuario is not None:
        q = q.filter(Usuario.Id_Usuario != excluir_id_usuario)
    return q.first()

# Vista unificada: registro y lista de usuarios
@router.get("/", response_class=HTMLResponse)
async def usuarios_view(
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    # Datos del usuario logueado
    id_unidad_academica = int(sess.id_unidad_academica)
    id_rol = int(sess.id_rol)
    id_usuario_logueado = int(sess.id_usuario)
    Rol = str(sess.nombre_rol)
    nombre_usuario = sess.nombre_usuario
    apellidoP_usuario = sess.apellidoP_usuario
    apellidoM_usuario = sess.apellidoM_usuario
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    
    # Verificar si es super admin
    es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
    
    # Verificar si tiene permisos administrativos
    tiene_permisos_admin = has_admin_permissions(db, id_rol)

    usuario_operador = str(getattr(sess, "usuario", "") or "sistema")
    unidad_operador = get_unidad_academica_nombre(db, id_unidad_academica)
    _, periodo_literal = get_ultimo_periodo(db)
    periodo_literal = periodo_literal or ""
    host_operador = get_request_host(request)

    usuarios = get_usuarios_vista_sp(
        db,
        usuario_operador=usuario_operador,
        unidad_academica=unidad_operador,
        periodo_literal=periodo_literal,
        host=host_operador,
    )

    # CASO ESPECIAL: Roles 7, 8, 9 pueden ver usuarios de todas las UAs (como superadmin)
    if es_super_admin or id_rol in [7, 8, 9]:
        nombre_ua = "Todas las Unidades Académicas"
    else:
        usuarios = [
            u
            for u in usuarios
            if int(u.get("id_unidad_academica") or 0) == id_unidad_academica
        ]
        nombre_ua = get_unidad_academica_nombre(db, id_unidad_academica)

    # FILTRO GLOBAL: NUNCA mostrar el superadmin 'admin admin admin' a nadie
    usuarios = [
        u
        for u in usuarios
        if not (
            str(u.get("nombre") or "").strip().lower() == "admin"
            and str(u.get("paterno") or "").strip().lower() == "admin"
            and str(u.get("materno") or "").strip().lower() == "admin"
        )
    ]

    # FILTRAR USUARIO ACTUAL DE LA SESIÓN (no mostrar su propio usuario en la lista)
    usuarios = [
        u for u in usuarios if int(u.get("id_usuario") or 0) != id_usuario_logueado
    ]
    
    # Filtrar roles según el grupo del rol del usuario logueado
    try:
        roles = get_roles_for_user_group(db, id_rol)
    except Exception:
        roles = get_all_roles(db)
    
    # FILTRAR ROLES DISPONIBLES según permisos del rol del usuario
    # Si es superadmin, puede ver todos los roles (excepto el suyo)
    if es_super_admin:
        roles_disponibles = [rol for rol in roles if rol.Id_Rol != id_rol]
    # Si el rol tiene permisos definidos, solo mostrar esos roles
    elif id_rol in PERMISOS_CREACION_ROLES:
        roles_permitidos = PERMISOS_CREACION_ROLES[id_rol]
        roles_disponibles = [rol for rol in roles if rol.Id_Rol in roles_permitidos]
    # Si no tiene permisos definidos, no puede crear usuarios
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
    
    unidades_academicas = get_all_units(db)
    niveles = get_all_niveles(db)
    formatos = get_formatos_activos(db)
    return templates.TemplateResponse(
        "usuarios.html",
        {
            "request": request,
            "usuarios": usuarios,
            "id_rol": id_rol,
            "id_unidad_academica": id_unidad_academica,
            "nombre_ua": nombre_ua,
            "nombre_usuario": nombre_completo,
            "roles": roles_disponibles,
            "unidades_academicas": unidades_academicas,
            "niveles": niveles,
            "formatos": formatos,
            "es_super_admin": es_super_admin,
            "tiene_permisos_admin": tiene_permisos_admin,
            "rol": Rol
        },
    )


# Endpoint para registrar usuario desde la misma página
@router.post("/registrar", response_class=JSONResponse)
async def registrar_usuario_view(
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    data = await request.json()
    try:
        user = UsuarioCreate(**data)

        formatos_ids = [int(x) for x in (data.get("Id_Formatos") or [])]
        if user.Id_Rol not in ROLES_SIN_FORMATO and not formatos_ids:
            return JSONResponse(
                status_code=400,
                content={"detail": "Debes seleccionar al menos un formato."},
            )

        data["Id_Formatos"] = formatos_ids
        
        # Obtener datos del usuario que está registrando
        id_rol_registrador = int(sess.id_rol)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
        
        # VALIDACIÓN 1: Verificar que el usuario tenga permiso para crear este rol
        if not es_super_admin:
            if id_rol_registrador not in PERMISOS_CREACION_ROLES:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "No tienes permisos para crear usuarios."}
                )
            
            roles_permitidos = PERMISOS_CREACION_ROLES[id_rol_registrador]
            if user.Id_Rol not in roles_permitidos:
                return JSONResponse(
                    status_code=403,
                    content={"detail": f"No tienes permisos para crear un usuario con este rol."}
                )
        
        # VALIDACIÓN 2: Restricciones de cantidad por rol
        # Rol 4 y 5: Solo 1 por Unidad Académica
        if user.Id_Rol in [4, 5]:
            usuario_existente = db.query(Usuario).filter(
                Usuario.Id_Rol == user.Id_Rol,
                Usuario.Id_Unidad_Academica == user.Id_Unidad_Academica,
                Usuario.Id_Estatus == 1
            ).first()
            
            if usuario_existente:
                nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                rol_nombre = "Director/a de DII" if user.Id_Rol == 4 else "Jefe/a de Departamento"
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": f"Ya existe un {rol_nombre} en esta Unidad Académica: {nombre_existente}"
                    }
                )

        # Roles superiores 6-9: solo uno activo por rol.
        if user.Id_Rol in ROLES_SUPERIORES_UNICOS:
            usuario_existente = _usuario_activo_por_rol(db, user.Id_Rol)
            if usuario_existente:
                nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                rol_nombres = {6: "Analista", 7: "Jefe/a de División", 8: "Titular", 9: "Administrador General"}
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": f"Ya existe un {rol_nombres.get(user.Id_Rol, 'usuario')} activo: {nombre_existente}"
                    }
                )

        resultado = registrar_usuario_sp(
            db,
            payload=data,
            usuario_operador=str(getattr(sess, "usuario", "") or "sistema"),
            host=get_request_host(request),
            generar_password_automatica=True,
        )

        return JSONResponse(content={"Id_Usuario": resultado["Id_Usuario"]})
    except Exception as e:
        msg = str(e)
        if "La persona ya esta registrada" in msg or "La persona ya está registrada" in msg:
            return JSONResponse(status_code=400, content={"detail": "La persona ya está registrada"})
        if "Email ya esta registrado" in msg or "Email ya está registrado" in msg:
            return JSONResponse(status_code=400, content={"detail": "Email ya está registrado"})
        return JSONResponse(status_code=400, content={"detail": msg})

# Endpoint para editar usuario desde la misma página
@router.post("/editar/{id_usuario}", response_class=JSONResponse)
async def editar_usuario_ajax(
    id_usuario: int,
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    try:
        data = await request.json()
        formatos_ids = [int(x) for x in (data.get("Id_Formatos") or [])]
        data["Id_Formatos"] = formatos_ids
        
        # Obtener datos del usuario que está editando
        id_rol_editor = int(sess.id_rol)
        nombre_usuario = sess.nombre_usuario
        apellidoP_usuario = sess.apellidoP_usuario
        apellidoM_usuario = sess.apellidoM_usuario
        es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
        
        # Obtener el usuario actual para comparar
        usuario_actual = db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()
        if not usuario_actual:
            return JSONResponse(
                status_code=404,
                content={"mensaje": "Usuario no encontrado."}
            )

        nuevo_id_rol = int(data.get("Id_Rol") or usuario_actual.Id_Rol)
        nueva_id_unidad = int(data.get("Id_Unidad_Academica") or usuario_actual.Id_Unidad_Academica)

        if nuevo_id_rol not in ROLES_SIN_FORMATO and not formatos_ids:
            return JSONResponse(
                status_code=400,
                content={"mensaje": "Debes seleccionar al menos un formato."},
            )
        
        # VALIDACIÓN 1: Verificar que el usuario tenga permiso para asignar este rol
        if not es_super_admin:
            if id_rol_editor not in PERMISOS_CREACION_ROLES:
                return JSONResponse(
                    status_code=403,
                    content={"mensaje": "No tienes permisos para editar usuarios."}
                )
            
            roles_permitidos = PERMISOS_CREACION_ROLES[id_rol_editor]
            if nuevo_id_rol not in roles_permitidos:
                return JSONResponse(
                    status_code=403,
                    content={"mensaje": "No tienes permisos para asignar este rol."}
                )
        
        # VALIDACIÓN 2: Si cambió el rol, verificar restricciones de cantidad
        if nuevo_id_rol != usuario_actual.Id_Rol:
            # Rol 4 y 5: Solo 1 por Unidad Académica
            if nuevo_id_rol in [4, 5]:
                usuario_existente = db.query(Usuario).filter(
                    Usuario.Id_Rol == nuevo_id_rol,
                    Usuario.Id_Unidad_Academica == nueva_id_unidad,
                    Usuario.Id_Estatus == 1,
                    Usuario.Id_Usuario != id_usuario
                ).first()
                
                if usuario_existente:
                    nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                    rol_nombre = "Director/a de DII" if nuevo_id_rol == 4 else "Jefe/a de Departamento"
                    return JSONResponse(
                        status_code=400,
                        content={
                            "mensaje": f"Ya existe un {rol_nombre} en esta Unidad Académica: {nombre_existente}"
                        }
                    )

            # Roles superiores 6-9: solo uno activo por rol.
            if nuevo_id_rol in ROLES_SUPERIORES_UNICOS:
                usuario_existente = _usuario_activo_por_rol(db, nuevo_id_rol, excluir_id_usuario=id_usuario)
                if usuario_existente:
                    nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                    rol_nombres = {6: "Analista", 7: "Jefe/a de División", 8: "Titular", 9: "Administrador General"}
                    return JSONResponse(
                        status_code=400,
                        content={
                            "mensaje": f"Ya existe un {rol_nombres.get(nuevo_id_rol, 'usuario')} activo: {nombre_existente}"
                        }
                    )

        modificar_usuario_sp(
            db,
            id_usuario=id_usuario,
            payload=data,
            usuario_operador=str(getattr(sess, "usuario", "") or "sistema"),
            host=get_request_host(request),
        )

        return JSONResponse(content={"mensaje": "Usuario actualizado correctamente."})
    except ValueError as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)

# Baja lógica de usuario (Id_Estatus = 3)
@router.post("/eliminar/{id_usuario}", response_class=JSONResponse)
async def eliminar_usuario(
    id_usuario: int,
    request: Request, sess=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    try:
        baja_usuario_sp(
            db,
            id_usuario=id_usuario,
            usuario_operador=str(getattr(sess, "usuario", "") or "sistema"),
            host=get_request_host(request),
        )

        return JSONResponse(content={"mensaje": "Usuario dado de baja correctamente."})
    except ValueError as e:
        msg = str(e)
        status = 404 if "no encontrado" in msg.lower() else 400
        return JSONResponse(content={"mensaje": msg}, status_code=status)
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)
