from backend.crud.Usuario import (
    create_usuario,
    read_user_by_username,
    read_user_by_email,
    read_password_by_user,
    read_password_by_email,
    update_usuario as crud_update_usuario,
    set_usuario_estatus as crud_set_usuario_estatus,
    get_usuarios_by_unidad as crud_get_usuarios_by_unidad,
    get_usuario_by_id as crud_get_usuario_by_id,
)
from backend.services.bitacora_service import registrar_bitacora
from backend.services.periodo_service import get_ultimo_periodo
from backend.database.models.Usuario import Usuario
from backend.utils.security import hash_password, generate_random_password
from backend.utils.request import get_request_host
from backend.utils.email import send_email, EmailSendError
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse, UsuarioLogin


from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict
import unicodedata

import bcrypt

class UserAlreadyExistsError(Exception):
    """Excepción lanzada cuando un usuario ya existe."""
    pass

def capitalizar_nombre(texto: str) -> str:
    """
    Capitaliza cada palabra del texto (primera letra mayúscula, resto minúscula).
    Maneja casos especiales como nombres compuestos y espacios múltiples.
    """
    if not texto:
        return texto
    
    # Dividir por espacios, capitalizar cada palabra y reunir
    palabras = texto.strip().split()
    palabras_capitalizadas = [palabra.capitalize() for palabra in palabras]
    return ' '.join(palabras_capitalizadas)

def get_username_by_email(db: Session, email: str) -> str | None:
    user = read_user_by_email(db, email)
    return user.Usuario if user else None


def _normalizar_texto_accion(texto: str) -> str:
    """Normaliza texto para comparaciones estables (sin acentos y en minúsculas)."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return texto.lower().strip()

def has_temporary_password(db: Session, user_id: int) -> bool:
    """Verifica si el usuario tiene contraseña temporal consultando SOLO la bitácora.
    Busca la acción MÁS RECIENTE relacionada con contraseñas.
    Si la más reciente es 'temporal generada' → requiere cambio
    Si la más reciente es 'cambió contraseña' → NO requiere cambio
    """
    try:
        from backend.database.models.Bitacora import Bitacora

        # Recuperar acciones más recientes del usuario sin acotar por 30 días,
        # para evitar falsos negativos cuando la contraseña temporal es antigua.
        acciones_recientes = (
            db.query(Bitacora)
            .filter(
                Bitacora.Id_Usuario == user_id
            )
            .order_by(Bitacora.Fecha.desc(), Bitacora.Id_Bitacora.desc())
            .limit(200)
            .all()
        )

        patrones_temporal = (
            "contrasena temporal",
            "password temporal",
            "contrasena provisional",
            "password provisional",
            "nueva contrasena temporal",
            "reset password",
        )
        patrones_cambio = (
            "cambio de contrasena",
            "cambio su contrasena",
            "contrasena actualizada",
            "actualizo su contrasena",
            "actualizo contrasena",
            "password actualizado",
        )
        
        # Buscar la PRIMERA acción relevante (más reciente)
        for accion in acciones_recientes:
            texto_accion = _normalizar_texto_accion(accion.Acciones or "")
            
            # Verificar si es acción de contraseña
            es_temporal = any(patron in texto_accion for patron in patrones_temporal)
            es_cambio = any(patron in texto_accion for patron in patrones_cambio)
            
            if es_temporal:
                # La acción más reciente es generación de temporal → SÍ requiere cambio
                return True
            
            if es_cambio:
                # La acción más reciente es cambio de contraseña → NO requiere cambio
                return False
        
        # No se encontró ninguna acción relevante
        return False
        
    except Exception as e:
        print(f"⚠️ Error verificando contraseña temporal: {e}")
        return False

# Funciones para manejo de contraseñas
def reset_password(db: Session, username: str, email: str, request = None) -> bool:
    """Genera una contraseña temporal y la envía al correo si username & email coinciden.
    Respuesta siempre booleana sin detallar causa para no filtrar existencia.
    """
    try:
        user = read_user_by_username(db, username)
        if not user or user.Email.lower() != email.lower():
            # Responder éxito falso pero sin detalle
            return False
        nueva = generate_random_password()
        user.Password = hash_password(nueva)
        from datetime import datetime, timezone
        user.Fecha_Modificacion = datetime.now(timezone.utc)
        db.commit()
        
        # Registrar en bitácora que se generó contraseña temporal
        try:
            from backend.services.bitacora_service import registrar_bitacora
            import socket
            
            id_modulo = 1  # Módulo de seguridad
            id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
            if not id_periodo:
                id_periodo = 1  # Fallback solo si no hay periodos
            accion = f"Nueva contraseña temporal generada para {user.Usuario}"

            # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
            host = get_request_host(request)
            
            # Registrar en la bitácora
            registrar_bitacora(
                db=db,
                id_usuario=user.Id_Usuario,
                id_modulo=id_modulo,
                id_periodo=id_periodo,
                accion=accion,
                host=host
            )
            print(f"✅ Bitácora registrada: Nueva contraseña temporal para usuario {user.Id_Usuario} desde host {host}")
        except Exception as bitacora_error:
            print(f"❌ Error al registrar en bitácora: {bitacora_error}")
            # No fallar el registro por error en bitácora
        # Enviar correo
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #6e0343; text-align: center;">Recuperación de Contraseña</h2>
                <p>Hola <strong>{user.Nombre}</strong>,</p>
                <p>Se ha generado una nueva contraseña temporal para tu cuenta.</p>
                <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Contraseña temporal:</strong> <span style="color: #6e0343; font-size: 18px; font-weight: bold;">{nueva}</span></p>
                </div>
                <p style="color: #d9534f; font-weight: bold;">⚠️ Por seguridad, cámbiela después de Iniciar Sesión.</p>
                <p style="margin-top: 20px;">Para acceder al sistema, haz clic en el siguiente enlace:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="http://148.204.107.39:50000" style="display: inline-block; padding: 12px 30px; background-color: #6e0343; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Acceder al Sistema SAE</a>
                </p>
                <p style="color: #666; font-size: 12px;">O copia y pega este enlace en tu navegador:<br>
                <a href="http://148.204.107.39:50000" style="color: #6e0343;">http://148.204.107.39:50000</a></p>
                <p style="margin-top: 30px;">Gracias,<br><strong>Sistema SAE</strong></p>
            </div>
        </body>
        </html>
        """
        try:
            send_email(user.Email, "Recuperación de contraseña", cuerpo)
        except EmailSendError:
            # Revertir si falla envío
            db.rollback()
            return False
        return True
    except Exception:
        db.rollback()
        return False

def change_password(db: Session, user_id: int, request, new_password: str) -> bool:
    """
    Cambiar la contraseña del usuario SIN requerir la contraseña actual.
    Solo necesita el ID del usuario y la nueva contraseña.
    También desmarca el flag de contraseña temporal.
    """
    user = db.query(Usuario).filter(Usuario.Id_Usuario == user_id).first()
    if not user:
        return False
    
    # Actualizar directamente sin validar contraseña actual
    user.Password = hash_password(new_password)
    from datetime import datetime, timezone
    user.Fecha_Modificacion = datetime.now(timezone.utc)
    db.commit()
    
    # Registrar en bitácora que cambió a contraseña personal
    try:
        from backend.services.bitacora_service import registrar_bitacora
        import socket
        
        id_modulo = 1  # Módulo de seguridad
        id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
        if not id_periodo:
            id_periodo = 1  # Fallback solo si no hay periodos
        accion = f"Usuario cambió su contraseña"

        # Obtener el hostname del cliente (reverse DNS). Si falla, usar IP.
        host = get_request_host(request)
        
        # Registrar en la bitácora
        registrar_bitacora(
            db=db,
            id_usuario=user_id,
            id_modulo=id_modulo,
            id_periodo=id_periodo,
            accion=accion,
            host=host
        )
        print(f"✅ Bitácora registrada: Cambio de contraseña para usuario {user_id} desde host {host}")
    except Exception as bitacora_error:
        print(f"❌ Error al registrar en bitácora: {bitacora_error}")
        # No fallar el cambio de contraseña por error en bitácora
    
    return True

#Funciones read
def user_already_exists(db: Session, username: str, email: str) -> bool:
    """Verifica si el usuario ya existe por nombre de usuario o email."""
    return read_user_by_username(db, username) is not None \
        or read_user_by_email(db, email) is not None

# Validar usuario por username/email y password
def validacion_usuario(db: Session, username_email: Optional[str], password: Optional[str]) -> bool:
    try:
        if username_email is not None and password is not None:
            user = read_user_by_email(db, username_email)
            if user is None:
                user = read_user_by_username(db, username_email)
            if user is None:
                return False  
            stored_password: Optional[str] = user.Password
            if stored_password is None:
                return False
            if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        print(f"Error en validacion_usuario: {e}")
        return False

# Validar usuario usando un objeto UsuarioLogin
def validacion_usuario_2(db: Session, userlogin: Optional[UsuarioLogin]) -> bool:
    """ Validar usuario usando un objeto UsuarioLogin """
    try:
        if userlogin is not None:
            user = read_user_by_email(db, userlogin.Usuario)
            if user is None:
                user = read_user_by_username(db, userlogin.Email)
            if user is None:
                return False
            stored_password: Optional[str] = user.Password
            if stored_password is None:
                return False
            if bcrypt.checkpw(userlogin.Password.encode("utf-8"), stored_password.encode("utf-8")):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:        
        print(f"Error en validacion_usuario: {e}")
        return False
            
#Funciones create
# Registrar un nuevo usuario
def register_usuario(db: Session, user_dict: UsuarioCreate, generar_password_automatica: bool = True) -> UsuarioResponse:
    """Registrar un nuevo usuario. Si generar_password_automatica=True, genera contraseña aleatoria y la envía por correo."""
    try:
        # NORMALIZAR NOMBRES: Capitalizar primera letra de cada palabra
        user_dict.Nombre = capitalizar_nombre(user_dict.Nombre)
        user_dict.Paterno = capitalizar_nombre(user_dict.Paterno)
        user_dict.Materno = capitalizar_nombre(user_dict.Materno)
        
        print(f"📝 Nombres normalizados: {user_dict.Nombre} {user_dict.Paterno} {user_dict.Materno}")

        # 1) Validar nombre completo (Nombre, Paterno, Materno) para evitar duplicidad de persona (solo activos)
        persona_existente = (
            db.query(Usuario)
            .filter(
                Usuario.Nombre == user_dict.Nombre,
                Usuario.Paterno == user_dict.Paterno,
                Usuario.Materno == user_dict.Materno,
                Usuario.Id_Estatus != 3
            )
            .first()
        )
        if persona_existente:
            raise ValueError("La persona ya está registrada")

        # 2) Validar usuario único (campo Usuario)
        usuario_existente = db.query(Usuario).filter(Usuario.Usuario == user_dict.Usuario).first()
        usuario_reactivado = False
        
        if usuario_existente:
            if usuario_existente.Id_Estatus != 3:
                raise ValueError("El nombre de usuario ya está registrado y activo.")
            # Si el usuario existe pero está dado de baja (estatus 3), REACTIVARLO
            print(f"♻️ Usuario {user_dict.Usuario} existe con estatus 3, reactivando...")
            usuario_reactivado = True

        # 3) Validar email (usuario se deriva del email)
        email_existente = db.query(Usuario).filter(Usuario.Email == user_dict.Email).first()
        if email_existente and email_existente.Id_Estatus != 3:
            raise ValueError("Email ya está registrado")

        # Generar contraseña temporal aleatoria si está activado o si no se proporcionó contraseña
        password_temporal = None
        if generar_password_automatica or user_dict.Password is None:
            password_temporal = generate_random_password()
            user_dict.Password = hash_password(password_temporal)
            print(f"✅ Contraseña temporal generada para {user_dict.Usuario}: {password_temporal}")
        else:
            # Usar la contraseña proporcionada (flujo antiguo)
            user_dict.Password = hash_password(user_dict.Password)
        
        # Si el usuario está siendo reactivado, actualizar en lugar de crear
        if usuario_reactivado and usuario_existente:
            from datetime import datetime, timezone
            # Actualizar datos del usuario existente
            usuario_existente.Nombre = user_dict.Nombre
            usuario_existente.Paterno = user_dict.Paterno
            usuario_existente.Materno = user_dict.Materno
            usuario_existente.Email = user_dict.Email
            usuario_existente.Password = user_dict.Password
            usuario_existente.Id_Unidad_Academica = user_dict.Id_Unidad_Academica
            usuario_existente.Id_Rol = user_dict.Id_Rol
            usuario_existente.Id_Nivel = user_dict.Id_Nivel if hasattr(user_dict, 'Id_Nivel') else None
            usuario_existente.Id_Estatus = 1  # REACTIVAR
            usuario_existente.Fecha_Modificacion = datetime.now(timezone.utc)
            usuario_existente.Fecha_Final = None  # Limpiar fecha de baja
            db.commit()
            db.refresh(usuario_existente)
            user = usuario_existente
            print(f"✅ Usuario {user.Usuario} reactivado exitosamente (ID: {user.Id_Usuario})")
        else:
            # Crear nuevo usuario
            user = create_usuario(db, user_dict)
        
        # Si se generó contraseña temporal, registrar en bitácora y enviar correo
        if generar_password_automatica and password_temporal:
            db.commit()
            db.refresh(user)
            
            # REGISTRAR EN BITÁCORA (PERSISTENTE)
            try:
                id_modulo = 1  # Módulo de seguridad
                id_periodo, _ = get_ultimo_periodo(db)  # Periodo dinámico
                if not id_periodo:
                    id_periodo = 1  # Fallback solo si no hay periodos
                accion = f"Contraseña temporal generada para usuario {user.Usuario}"
                host = "sistema"  # No tenemos request aquí, usar valor por defecto
                
                registrar_bitacora(
                    db=db,
                    id_usuario=user.Id_Usuario,
                    id_modulo=id_modulo,
                    id_periodo=id_periodo,
                    accion=accion,
                    host=host
                )
                print(f"✅ Bitácora registrada: Contraseña temporal para usuario {user.Id_Usuario}")
            except Exception as bitacora_error:
                print(f"❌ Error al registrar en bitácora: {bitacora_error}")
            
            # Enviar correo con la contraseña temporal
            nombre_completo = f"{user.Nombre or ''} {user.Paterno or ''} {user.Materno or ''}".strip()
            cuerpo = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #6e0343; text-align: center;">Bienvenid@ al SAE</h2>
                    <h2 style="color: #6e0343; text-align: center;">"Sistema de Administración y Estadística"</h2>
                    <p>Hola <strong>{nombre_completo}</strong>,</p>
                    <p>Tu cuenta ha sido creada exitosamente. A continuación encontrarás tus credenciales de acceso:</p>
                    <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Usuario:</strong> {user.Usuario}</p>
                        <p><strong>Contraseña temporal:</strong> <span style="color: #6e0343; font-size: 18px; font-weight: bold;">{password_temporal}</span></p>
                    </div>
                    <p style="color: #d9534f; font-weight: bold;">⚠️ IMPORTANTE:</p>
                    <ul>
                        <li>Esta es una contraseña <strong>temporal</strong> generada automáticamente</li>
                        <li>Deberás cambiarla por una contraseña segura en tu primer inicio de sesión</li>
                        <li>No compartas esta contraseña con nadie</li>
                    </ul>
                    <p style="margin-top: 20px;">Para acceder al sistema, haz clic en el siguiente enlace:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="http://148.204.107.39:50000" style="display: inline-block; padding: 12px 30px; background-color: #6e0343; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Acceder al Sistema SAE</a>
                    </p>
                    <p style="color: #666; font-size: 12px;">O copia y pega este enlace en tu navegador:<br>
                    <a href="http://148.204.107.39:50000" style="color: #6e0343;">http://148.204.107.39:50000</a></p>
                    <p style="margin-top: 30px;">Gracias,<br><strong>Equipo del Sistema SAE</strong></p>
                </div>
            </body>
            </html>
            """
            try:
                send_email(user.Email, "Credenciales de acceso - Sistema SAE", cuerpo)
                print(f"✅ Correo enviado exitosamente a {user.Email}")
            except EmailSendError as email_error:
                print(f"❌ Error al enviar correo: {email_error}")
                # No revertir el registro, solo advertir
                raise ValueError(f"Usuario registrado pero no se pudo enviar el correo. Contacte al administrador.")
        
        return UsuarioResponse.model_validate(user)

    except IntegrityError as e:
        # Respaldo por condiciones de carrera: mapear todo a email (política solicitada)
        msg = str(e.orig).lower()
        if ("email" in msg) or ("correo" in msg) or ("usuario" in msg):
            raise ValueError("Email ya está registrado")
        raise
    except Exception as e:
        print(f"Error en usuario_services: {e}")
        raise
    finally:
        db.close()

# Obtener todos los usuarios de una Unidad Académica
def get_usuarios_by_unidad(db: Session, id_unidad_academica: int):
    return crud_get_usuarios_by_unidad(db, id_unidad_academica)

# Obtener un usuario por su ID
def get_usuario_by_id(db: Session, id_usuario: int):
    return crud_get_usuario_by_id(db, id_usuario)

# Actualizar un usuario
def update_usuario(
    db: Session,
    id_usuario: int,
    Nombre: str,
    Paterno: str,
    Materno: str,
    Email: str,
    Id_Rol: int,
    Usuario: Optional[str] = None,
    Id_Unidad_Academica: Optional[int] = None,
    Id_Nivel: Optional[int] = None,
):
    return crud_update_usuario(
        db,
        id_usuario,
        Nombre,
        Paterno,
        Materno,
        Email,
        Id_Rol,
        UsuarioStr=Usuario,
        Id_Unidad_Academica=Id_Unidad_Academica,
        Id_Nivel=Id_Nivel,
    )

# Cambiar estatus de un usuario (baja lógica)
def set_usuario_estatus(db: Session, id_usuario: int, id_estatus: int):
    return crud_set_usuario_estatus(db, id_usuario, id_estatus)

# Obtener todos los roles
def get_all_roles(db: Session):
    from backend.database.models.CatRoles import CatRoles
    return db.query(CatRoles).all()

# Obtener usuarios por unidad académica junto con el nombre del rol
def get_usuarios_by_unidad_con_rol(db: Session, id_unidad_academica: int):
    from backend.database.models.Usuario import Usuario
    from backend.database.models.CatRoles import CatRoles
    from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
    return (
        db.query(Usuario, CatRoles.Rol.label("NombreRol"), CatUnidadAcademica.Sigla.label("SiglaUA"))
        .join(CatRoles, Usuario.Id_Rol == CatRoles.Id_Rol)
        .join(CatUnidadAcademica, Usuario.Id_Unidad_Academica == CatUnidadAcademica.Id_Unidad_Academica)
        .filter(
            Usuario.Id_Unidad_Academica == id_unidad_academica,
            Usuario.Id_Estatus != 3
        )
        .all()
    )

# Obtener el nombre de la Unidad Académica por su id
def get_unidad_academica_nombre(db: Session, id_unidad_academica: int) -> str:
    from backend.crud.CatUnidadAcademica import read_unidad_by_id
    ua = read_unidad_by_id(db, id_unidad_academica)
    return ua.Nombre if ua else "-"

# Verificar si un usuario es super admin (nombre completo "admin admin admin")
def is_super_admin(nombre: str, paterno: str, materno: str) -> bool:
    return (nombre.lower() == "admin" and 
            paterno.lower() == "admin" and 
            materno.lower() == "admin")

# Función para determinar si un rol tiene permisos administrativos
def has_admin_permissions(db: Session, id_rol: int) -> bool:
    """
    Determina si un rol tiene permisos administrativos basándose en el nombre del rol.
    Roles con permisos: Titular, Jefe/a de División, Jefe/a de Departamento, CEGET
    """
    from backend.database.models.CatRoles import CatRoles
    
    try:
        rol = db.query(CatRoles).filter(CatRoles.Id_Rol == id_rol).first()
        if not rol:
            return False
        
        # Roles con permisos administrativos (normalizar a minúsculas para comparación)
        rol_nombre = rol.Rol.lower()
        roles_admin = [
            'administrador',
            'titular', 
            'jefe/a de división',
            'jefe/a de departamento',
            'ceget'
        ]
        
        return any(admin_role in rol_nombre for admin_role in roles_admin)
    except Exception:
        return False

# Obtener TODOS los usuarios con rol (para super admin)
def get_all_usuarios_con_rol(db: Session):
    from backend.database.models.Usuario import Usuario
    from backend.database.models.CatRoles import CatRoles
    from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
    return (
        db.query(Usuario, CatRoles.Rol.label("NombreRol"), CatUnidadAcademica.Sigla.label("SiglaUA"))
        .join(CatRoles, Usuario.Id_Rol == CatRoles.Id_Rol)
        .join(CatUnidadAcademica, Usuario.Id_Unidad_Academica == CatUnidadAcademica.Id_Unidad_Academica)
        .filter(Usuario.Id_Estatus != 3)
        .all()
    )
