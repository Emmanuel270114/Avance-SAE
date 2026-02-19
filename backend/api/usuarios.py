from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from backend.core.templates import templates
from backend.database.connection import get_db
from backend.database.models.Usuario import Usuario
from backend.services.usuario_service import (
    get_usuarios_by_unidad,
    get_usuario_by_id,
    update_usuario,
    set_usuario_estatus,
    get_usuarios_by_unidad_con_rol,
    get_all_usuarios_con_rol,
    get_unidad_academica_nombre,
    register_usuario,
    is_super_admin,
    has_admin_permissions
)
from backend.services.roles_service import get_all_roles, get_roles_for_user_group
from backend.services.bitacora_service import registrar_bitacora
from backend.services.periodo_service import get_ultimo_periodo
from backend.services.unidad_services import get_all_units
from backend.services.nivel_service import get_all_niveles
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse
from sqlalchemy.orm import Session
import socket
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

# Vista unificada: registro y lista de usuarios
@router.get("/", response_class=HTMLResponse)
async def usuarios_view(
    request: Request,
    db: Session = Depends(get_db),
):
    # Datos del usuario logueado
    id_unidad_academica = int(request.cookies.get("id_unidad_academica", 1))
    id_rol = int(request.cookies.get("id_rol", 2))
    id_usuario_logueado = int(request.cookies.get("id_usuario", 0))
    Rol = str(request.cookies.get("nombre_rol",""))
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    nombre_completo = " ".join(filter(None, [nombre_usuario, apellidoP_usuario, apellidoM_usuario]))
    
    # Verificar si es super admin
    es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
    
    # Verificar si tiene permisos administrativos
    tiene_permisos_admin = has_admin_permissions(db, id_rol)
    
    # Obtener usuarios según privilegios
    # CASO ESPECIAL: Roles 7, 8, 9 pueden ver usuarios de todas las UAs (como superadmin)
    if es_super_admin or id_rol in [7, 8, 9]:
        usuarios_con_rol = get_all_usuarios_con_rol(db)
        nombre_ua = "Todas las Unidades Académicas"
    else:
        usuarios_con_rol = get_usuarios_by_unidad_con_rol(db, id_unidad_academica)
        nombre_ua = get_unidad_academica_nombre(db, id_unidad_academica)
    
    # FILTRO GLOBAL: NUNCA mostrar el superadmin 'admin admin admin' a nadie
    usuarios_con_rol = [u for u in usuarios_con_rol if not (
        getattr(u[0], 'Nombre', '').strip().lower() == 'admin' and
        getattr(u[0], 'Paterno', '').strip().lower() == 'admin' and
        getattr(u[0], 'Materno', '').strip().lower() == 'admin'
    )]
    
    # FILTRAR USUARIO ACTUAL DE LA SESIÓN (no mostrar su propio usuario en la lista)
    usuarios_con_rol = [u for u in usuarios_con_rol if getattr(u[0], 'Id_Usuario', None) != id_usuario_logueado]
    print(f"👤 Usuario logueado ID: {id_usuario_logueado} - Filtrado de la lista")
    
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
    
    unidades_academicas = get_all_units(db)
    niveles = get_all_niveles(db)
    return templates.TemplateResponse(
        "usuarios.html",
        {
            "request": request,
            "usuarios_con_rol": usuarios_con_rol,
            "id_rol": id_rol,
            "id_unidad_academica": id_unidad_academica,
            "nombre_ua": nombre_ua,
            "nombre_usuario": nombre_completo,
            "roles": roles_disponibles,
            "unidades_academicas": unidades_academicas,
            "niveles": niveles,
            "es_super_admin": es_super_admin,
            "tiene_permisos_admin": tiene_permisos_admin,
            "rol": Rol
        },
    )


# Endpoint para registrar usuario desde la misma página
@router.post("/registrar", response_class=JSONResponse)
async def registrar_usuario_view(
    request: Request,
    db: Session = Depends(get_db),
):
    data = await request.json()
    try:
        user = UsuarioCreate(**data)
        
        # Obtener datos del usuario que está registrando
        id_rol_registrador = int(request.cookies.get("id_rol", 2))
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
        apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
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
        
        # Rol 7, 8, 9: Solo 1 en total (global)
        if user.Id_Rol in [7, 8, 9]:
            usuario_existente = db.query(Usuario).filter(
                Usuario.Id_Rol == user.Id_Rol,
                Usuario.Id_Estatus == 1
            ).first()
            
            if usuario_existente:
                nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                rol_nombres = {7: "Jefe/a de División", 8: "Titular", 9: "Administrador General"}
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": f"Ya existe un {rol_nombres[user.Id_Rol]}: {nombre_existente}"
                    }
                )
        
        usuario_registrado = register_usuario(db, user)
        
        # Registro en la tabla Bitacora de la DB
        # Tomar el ID del usuario logueado desde la cookie
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            try:
                id_modulo = 1  # Puedes ajustar el ID del módulo según tu catálogo
                id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
                if not id_periodo:
                    id_periodo = 1  # Fallback solo si no hay periodos
                accion = f"Registró nuevo usuario con ID {usuario_registrado.Id_Usuario}"

                # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
                host = get_request_host(request)
                # Registrar en la bitácora
                registrar_bitacora(
                    db=db,
                    id_usuario=id_usuario_log,
                    id_modulo=id_modulo,
                    id_periodo=id_periodo,
                    accion=accion,
                    host=host
                )
                print(f"✅ Bitácora registrada: Usuario {id_usuario_log} registró usuario {usuario_registrado.Id_Usuario}")
            except Exception as bitacora_error:
                print(f"❌ Error al registrar en bitácora: {bitacora_error}")
                # No fallar el registro por error en bitácora
        
        return JSONResponse(content={"Id_Usuario": usuario_registrado.Id_Usuario})
    except Exception as e:
        msg = str(e)
        if "La persona ya está registrada" in msg:
            return JSONResponse(status_code=400, content={"detail": "La persona ya está registrada"})
        if "Email ya está registrado" in msg:
            return JSONResponse(status_code=400, content={"detail": "Email ya está registrado"})
        return JSONResponse(status_code=400, content={"detail": msg})

# Endpoint para editar usuario desde la misma página
@router.post("/editar/{id_usuario}", response_class=JSONResponse)
async def editar_usuario_ajax(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # Validar superadmin
    nombre_usuario = request.cookies.get("nombre_usuario", "")
    apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
    apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
    if not is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario):
        return JSONResponse(content={"mensaje": "No te puedes modificar a ti mismo."}, status_code=403)
    try:
        data = await request.json()
        nuevo_id_rol = data.get("Id_Rol")
        nueva_id_unidad = data.get("Id_Unidad_Academica")
        
        # Obtener datos del usuario que está editando
        id_rol_editor = int(request.cookies.get("id_rol", 2))
        nombre_usuario = request.cookies.get("nombre_usuario", "")
        apellidoP_usuario = request.cookies.get("apellidoP_usuario", "")
        apellidoM_usuario = request.cookies.get("apellidoM_usuario", "")
        es_super_admin = is_super_admin(nombre_usuario, apellidoP_usuario, apellidoM_usuario)
        
        # Obtener el usuario actual para comparar
        usuario_actual = get_usuario_by_id(db, id_usuario)
        if not usuario_actual:
            return JSONResponse(
                status_code=404,
                content={"mensaje": "Usuario no encontrado."}
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
            
            # Rol 7, 8, 9: Solo 1 en total (global)
            if nuevo_id_rol in [7, 8, 9]:
                usuario_existente = db.query(Usuario).filter(
                    Usuario.Id_Rol == nuevo_id_rol,
                    Usuario.Id_Estatus == 1,
                    Usuario.Id_Usuario != id_usuario
                ).first()
                
                if usuario_existente:
                    nombre_existente = f"{usuario_existente.Nombre} {usuario_existente.Paterno} {usuario_existente.Materno}".strip()
                    rol_nombres = {7: "Jefe/a de División", 8: "Titular", 9: "Administrador General"}
                    return JSONResponse(
                        status_code=400,
                        content={
                            "mensaje": f"Ya existe un {rol_nombres[nuevo_id_rol]}: {nombre_existente}"
                        }
                    )
        
        update_usuario(
            db,
            id_usuario,
            data.get("Nombre"),
            data.get("Paterno"),
            data.get("Materno"),
            data.get("Email"),
            data.get("Id_Rol"),
            data.get("Usuario"),
            data.get("Id_Unidad_Academica"),
            data.get("Id_Nivel")
        )
        # Registro en la tabla Bitacora de la DB
        # Tomar el ID del usuario logueado desde la cookie (no el modificado)
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            id_modulo = 1  # Puedes ajustar el ID del módulo según tu catálogo
            id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
            if not id_periodo:
                id_periodo = 1  # Fallback solo si no hay periodos
            accion = f"Modificó usuario con ID {id_usuario}"

            # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
            xff = request.headers.get("x-forwarded-for") or ""
            client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
            try:
                # Obtener el hostname a partir de la IP
                host = socket.gethostbyaddr(client_ip)[0] if client_ip else ""
            except Exception:
                host = client_ip
            # Registrar en la bitácora
            registrar_bitacora(
                db=db,
                id_usuario=id_usuario_log,
                id_modulo=id_modulo,
                id_periodo=id_periodo,
                accion=accion,
                host=host
            )
        return JSONResponse(content={"mensaje": "Usuario actualizado correctamente."})
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)

# Baja lógica de usuario (Id_Estatus = 3)
@router.post("/eliminar/{id_usuario}", response_class=JSONResponse)
async def eliminar_usuario(
    id_usuario: int,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        u = set_usuario_estatus(db, id_usuario, 3)
        if not u:
            return JSONResponse(content={"mensaje": "Usuario no encontrado"}, status_code=404)

        # Bitácora: quién elimina a quién
        id_usuario_log = request.cookies.get("id_usuario")
        try:
            id_usuario_log = int(id_usuario_log) if id_usuario_log is not None else 0
        except (TypeError, ValueError):
            id_usuario_log = 0
        if id_usuario_log > 0:
            id_modulo = 1
            id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
            if not id_periodo:
                id_periodo = 1  # Fallback solo si no hay periodos
            accion = f"Eliminó (baja lógica) usuario con ID {id_usuario}"
            host = get_request_host(request)
            registrar_bitacora(db=db, id_usuario=id_usuario_log, id_modulo=id_modulo, id_periodo=id_periodo, accion=accion, host=host)

        return JSONResponse(content={"mensaje": "Usuario dado de baja correctamente."})
    except Exception as e:
        return JSONResponse(content={"mensaje": str(e)}, status_code=500)
