from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.models.CatFormatos import CatFormatos
from backend.database.models.CatNivel import CatNivel
from backend.database.models.CatRoles import CatRoles
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.database.models.Usuario import Usuario
from backend.services.bitacora_service import registrar_bitacora
from backend.services.periodo_service import get_ultimo_periodo
from backend.utils.email import EmailSendError, send_email
from backend.utils.security import generate_random_password, hash_password


ROLES_SIN_NIVEL = {6, 7, 8, 9}
ROLES_SIN_FORMATO = {6, 7, 8, 9}


def _capitalizar_nombre(texto: str) -> str:
    if not texto:
        return texto
    palabras = texto.strip().split()
    return " ".join(palabra.capitalize() for palabra in palabras)


def _get_periodo_literal(db: Session) -> str:
    _, periodo_literal = get_ultimo_periodo(db)
    if not periodo_literal:
        raise ValueError("No hay periodos configurados en el sistema.")
    return periodo_literal


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError("Valor numerico invalido.") from e
    return parsed if parsed > 0 else None


def _resolver_catalogos(
    db: Session,
    id_unidad_academica: int,
    id_rol: int,
    id_nivel: int | None,
    id_formatos: list[int],
) -> tuple[CatUnidadAcademica, CatRoles, CatNivel | None, list[CatFormatos]]:
    unidad = (
        db.query(CatUnidadAcademica)
        .filter(CatUnidadAcademica.Id_Unidad_Academica == id_unidad_academica)
        .first()
    )
    if not unidad:
        raise ValueError("Unidad academica invalida.")

    rol = db.query(CatRoles).filter(CatRoles.Id_Rol == id_rol).first()
    if not rol:
        raise ValueError("Rol invalido.")

    nivel: CatNivel | None = None
    if id_rol in ROLES_SIN_NIVEL:
        if id_nivel:
            nivel = db.query(CatNivel).filter(CatNivel.Id_Nivel == id_nivel).first()
            if not nivel:
                raise ValueError("Nivel invalido.")
    else:
        if not id_nivel:
            raise ValueError("Debe seleccionar un nivel para este rol.")
        nivel = db.query(CatNivel).filter(CatNivel.Id_Nivel == id_nivel).first()
        if not nivel:
            raise ValueError("Nivel invalido.")

    formatos = (
        db.query(CatFormatos)
        .filter(CatFormatos.Id_Formato.in_(id_formatos), CatFormatos.Id_Estatus == 1)
        .all()
    )
    if len(formatos) != len(set(id_formatos)):
        raise ValueError("Uno o mas formatos no son validos o estan inactivos.")

    return unidad, rol, nivel, formatos


def _limpiar_temp_usuarios(db: Session, usuario_objetivo: str) -> None:
    db.execute(
        text("DELETE FROM Temp_Usuarios WHERE Usuario = :usuario"),
        {"usuario": usuario_objetivo},
    )


def _cargar_temp_usuarios(
    db: Session,
    usuario_objetivo: str,
    sigla_unidad: str,
    nombre_rol: str,
    email: str,
    nombre: str,
    paterno: str,
    materno: str,
    nombre_nivel: str,
    nombres_formatos: list[str],
) -> None:
    if not nombres_formatos:
        nombres_formatos = ["SIN_FORMATO"]

    _limpiar_temp_usuarios(db, usuario_objetivo)

    insert_sql = text(
        """
        INSERT INTO Temp_Usuarios
            (Sigla, Usuario, Rol, Email, Nombre, Paterno, Materno, Nivel, Formato)
        VALUES
            (:sigla, :usuario, :rol, :email, :nombre, :paterno, :materno, :nivel, :formato)
        """
    )

    for formato in nombres_formatos:
        db.execute(
            insert_sql,
            {
                "sigla": sigla_unidad,
                "rol": nombre_rol,
                "email": email,
                "nombre": nombre,
                "paterno": paterno,
                "materno": materno,
                "nivel": nombre_nivel,
                "usuario": usuario_objetivo,
                "formato": formato,
            },
        )


def _enviar_correo_bienvenida(
    *,
    email: str,
    nombre_completo: str,
    usuario: str,
    password_temporal: str,
) -> None:
    cuerpo = f"""
    <html>
    <body style=\"font-family: Arial, sans-serif; line-height: 1.6; color: #333;\">
        <div style=\"max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;\">
            <h2 style=\"color: #6e0343; text-align: center;\">Bienvenid@ al SAE</h2>
            <p>Hola <strong>{nombre_completo}</strong>,</p>
            <p>Tu cuenta fue creada exitosamente. Aqui estan tus credenciales de acceso:</p>
            <div style=\"background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;\">
                <p><strong>Usuario:</strong> {usuario}</p>
                <p><strong>Contrasena temporal:</strong> <span style=\"color: #6e0343; font-size: 18px; font-weight: bold;\">{password_temporal}</span></p>
            </div>
            <p style=\"color: #d9534f; font-weight: bold;\">Por seguridad, cambiala al iniciar sesion.</p>
            <p style=\"margin-top: 20px;\">Accede al sistema con el siguiente enlace:</p>
            <p style=\"text-align: center; margin: 30px 0;\">
                <a href=\"http://148.204.107.39:50000\" style=\"display: inline-block; padding: 12px 30px; background-color: #6e0343; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;\">Acceder al SAE</a>
            </p>
            <p style=\"margin-top: 30px;\">Gracias,<br><strong>Equipo SAE</strong></p>
        </div>
    </body>
    </html>
    """

    send_email(email, "Credenciales de acceso - Sistema SAE", cuerpo)


def _registrar_bitacora_password_temporal(
    db: Session,
    *,
    id_usuario: int,
    usuario: str,
    host: str,
) -> None:
    """Registra una marca persistente para detección de contraseña temporal en login."""
    try:
        id_periodo, _ = get_ultimo_periodo(db)
        if not id_periodo:
            id_periodo = 1
        registrar_bitacora(
            db=db,
            id_usuario=id_usuario,
            id_modulo=1,
            id_periodo=id_periodo,
            accion=f"Nueva contraseña temporal generada para {usuario}",
            host=host or "sistema",
        )
    except Exception as e:
        # No bloquear el alta/modificación por una falla en bitácora.
        print(f"⚠️ No se pudo registrar bitácora de contraseña temporal para {usuario}: {e}")


def _sincronizar_formatos_usuario(db: Session, id_usuario: int, id_formatos: list[int]) -> None:
    if not id_formatos:
        db.execute(
            text("DELETE FROM Formato_Usuario WHERE Id_Usuario = :id_usuario"),
            {"id_usuario": id_usuario},
        )
        return

    placeholders = ", ".join(f":f{i}" for i in range(len(id_formatos)))
    params = {"id_usuario": id_usuario, **{f"f{i}": v for i, v in enumerate(id_formatos)}}

    db.execute(
        text(
            f"""
            DELETE FROM Formato_Usuario
            WHERE Id_Usuario = :id_usuario
              AND Id_Formato NOT IN ({placeholders})
            """
        ),
        params,
    )

    upsert_sql = text(
        """
        IF EXISTS (
            SELECT 1
            FROM Formato_Usuario
            WHERE Id_Usuario = :id_usuario AND Id_Formato = :id_formato
        )
        BEGIN
            UPDATE Formato_Usuario
            SET Id_Estatus = 1,
                Fecha_Modificacion = GETDATE(),
                Fecha_Final = NULL
            WHERE Id_Usuario = :id_usuario AND Id_Formato = :id_formato
        END
        ELSE
        BEGIN
            INSERT INTO Formato_Usuario
                (Id_Formato, Id_Usuario, Fecha_Inicio, Fecha_Modificacion, Fecha_Final, Id_Estatus)
            VALUES
                (:id_formato, :id_usuario, GETDATE(), GETDATE(), NULL, 1)
        END
        """
    )

    for id_formato in id_formatos:
        db.execute(upsert_sql, {"id_usuario": id_usuario, "id_formato": id_formato})


def get_formatos_activos(db: Session) -> list[CatFormatos]:
    return (
        db.query(CatFormatos)
        .filter(CatFormatos.Id_Estatus == 1)
        .order_by(CatFormatos.Formato.asc())
        .all()
    )


def _row_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
    return ""


def get_usuarios_vista_sp(db: Session) -> list[dict[str, Any]]:
    result = db.execute(text("EXEC dbo.SP_Consulta_Usuarios"))
    rows = [dict(r) for r in result.mappings().all()]

    usuarios_activos = db.query(Usuario).filter(Usuario.Id_Estatus == 1).all()
    usuarios_por_username = {u.Usuario.lower(): u for u in usuarios_activos if u.Usuario}

    roles_map = {r.Id_Rol: r.Rol for r in db.query(CatRoles).all()}
    niveles_map = {n.Id_Nivel: n.Nivel for n in db.query(CatNivel).all()}
    unidades_map = {u.Id_Unidad_Academica: u.Sigla for u in db.query(CatUnidadAcademica).all()}

    formatos_rows = db.execute(
        text(
            """
            SELECT u.Usuario, cf.Id_Formato, cf.Formato
            FROM Usuarios u
            LEFT JOIN Formato_Usuario fu ON fu.Id_Usuario = u.Id_Usuario AND fu.Id_Estatus = 1
            LEFT JOIN Cat_Formatos cf ON cf.Id_Formato = fu.Id_Formato AND cf.Id_Estatus = 1
            WHERE u.Id_Estatus = 1
            """
        )
    ).mappings().all()

    formatos_por_usuario: dict[str, dict[str, Any]] = {}
    for row in formatos_rows:
        username = str(row.get("Usuario") or "").strip().lower()
        if not username:
            continue

        entry = formatos_por_usuario.setdefault(username, {"ids": set(), "nombres": set()})
        id_formato = row.get("Id_Formato")
        formato_nombre = row.get("Formato")

        if id_formato:
            entry["ids"].add(int(id_formato))
        if formato_nombre:
            entry["nombres"].add(str(formato_nombre).strip())

    agrupados: dict[str, dict[str, Any]] = {}
    for row in rows:
        username = _row_value(row, "Usuario", "usuario")
        if not username:
            continue

        key = username.lower()
        usuario_model = usuarios_por_username.get(key)
        if not usuario_model:
            continue

        if key not in agrupados:
            agrupados[key] = {
                "id_usuario": int(usuario_model.Id_Usuario),
                "nombre": _row_value(row, "Nombre", "nombre") or (usuario_model.Nombre or ""),
                "paterno": _row_value(row, "Paterno", "paterno") or (usuario_model.Paterno or ""),
                "materno": _row_value(row, "Materno", "materno") or (usuario_model.Materno or ""),
                "usuario": username,
                "email": _row_value(row, "Email", "email") or (usuario_model.Email or ""),
                "id_unidad_academica": int(usuario_model.Id_Unidad_Academica or 0),
                "sigla_ua": _row_value(row, "SIGLA", "Sigla", "sigla") or unidades_map.get(int(usuario_model.Id_Unidad_Academica or 0), ""),
                "id_rol": int(usuario_model.Id_Rol or 0),
                "rol": _row_value(row, "Rol", "rol") or roles_map.get(int(usuario_model.Id_Rol or 0), ""),
                "id_nivel": int(usuario_model.Id_Nivel or 0),
                "nivel": _row_value(row, "Nivel", "nivel") or niveles_map.get(int(usuario_model.Id_Nivel or 0), ""),
                "formatos_ids": [],
                "formatos_nombres": [],
                "formatos_texto": "Sin formato",
            }

    salida: list[dict[str, Any]] = []
    for username_key, item in agrupados.items():
        formatos_info = formatos_por_usuario.get(username_key, {"ids": set(), "nombres": set()})
        ids = sorted(list(formatos_info["ids"]))
        nombres = sorted(list(formatos_info["nombres"]))

        item["formatos_ids"] = ids
        item["formatos_nombres"] = nombres
        item["formatos_texto"] = ", ".join(nombres) if nombres else "Sin formato"
        salida.append(item)

    salida.sort(key=lambda u: ((u.get("nombre") or "").lower(), (u.get("paterno") or "").lower(), (u.get("materno") or "").lower()))
    return salida


def registrar_usuario_sp(
    db: Session,
    payload: dict[str, Any],
    usuario_operador: str,
    host: str,
    generar_password_automatica: bool = True,
) -> dict[str, Any]:
    usuario_nuevo = str(payload.get("Usuario") or "").strip()
    email = str(payload.get("Email") or "").strip()
    nombre = _capitalizar_nombre(str(payload.get("Nombre") or "").strip())
    paterno = _capitalizar_nombre(str(payload.get("Paterno") or "").strip())
    materno = _capitalizar_nombre(str(payload.get("Materno") or "").strip())

    id_unidad = int(payload.get("Id_Unidad_Academica") or 0)
    id_rol = int(payload.get("Id_Rol") or 0)
    id_nivel = _to_optional_int(payload.get("Id_Nivel"))
    id_formatos = [int(x) for x in (payload.get("Id_Formatos") or [])]

    if not usuario_nuevo:
        raise ValueError("El campo Usuario es obligatorio.")
    if not email:
        raise ValueError("El campo Email es obligatorio.")
    if not id_formatos and id_rol not in ROLES_SIN_FORMATO:
        raise ValueError("Debes seleccionar al menos un formato.")

    persona_existente = (
        db.query(Usuario)
        .filter(
            Usuario.Nombre == nombre,
            Usuario.Paterno == paterno,
            Usuario.Materno == materno,
            Usuario.Id_Estatus == 1,
        )
        .first()
    )
    if persona_existente:
        raise ValueError("La persona ya esta registrada")

    usuario_existente = db.query(Usuario).filter(Usuario.Usuario == usuario_nuevo).first()
    reactivar_usuario = False
    if usuario_existente:
        estatus_usuario = int(usuario_existente.Id_Estatus or 0)
        if estatus_usuario == 1:
            raise ValueError("El nombre de usuario ya esta registrado y activo.")
        if estatus_usuario == 3:
            raise ValueError("El nombre de usuario esta marcado como eliminado y no puede reactivarse.")
        if estatus_usuario == 2:
            reactivar_usuario = True

    email_existente = db.query(Usuario).filter(Usuario.Email == email).first()
    if email_existente:
        if not usuario_existente or int(email_existente.Id_Usuario) != int(usuario_existente.Id_Usuario):
            if int(email_existente.Id_Estatus or 0) == 1:
                raise ValueError("Email ya esta registrado")
            raise ValueError("El email pertenece a otro usuario existente.")
        if int(email_existente.Id_Estatus or 0) == 3:
            raise ValueError("El email esta marcado como eliminado y no puede reutilizarse.")

    unidad, rol, nivel, formatos = _resolver_catalogos(db, id_unidad, id_rol, id_nivel, id_formatos)

    if generar_password_automatica:
        password_temporal = generate_random_password()
    else:
        pwd_payload = str(payload.get("Password") or "").strip()
        if not pwd_payload:
            raise ValueError("No se proporciono contrasena para el registro.")
        password_temporal = pwd_payload

    password_hash = hash_password(password_temporal)
    periodo_literal = _get_periodo_literal(db)

    if reactivar_usuario and usuario_existente:
        usuario_existente.Nombre = nombre
        usuario_existente.Paterno = paterno
        usuario_existente.Materno = materno
        usuario_existente.Email = email
        usuario_existente.Password = password_hash
        usuario_existente.Id_Unidad_Academica = id_unidad
        usuario_existente.Id_Rol = id_rol
        usuario_existente.Id_Nivel = id_nivel
        usuario_existente.Id_Estatus = 1
        usuario_existente.Fecha_Modificacion = datetime.now(timezone.utc)
        usuario_existente.Fecha_Final = None

        _sincronizar_formatos_usuario(
            db,
            id_usuario=int(usuario_existente.Id_Usuario),
            id_formatos=id_formatos,
        )

        db.commit()
        db.refresh(usuario_existente)

        _registrar_bitacora_password_temporal(
            db,
            id_usuario=int(usuario_existente.Id_Usuario),
            usuario=usuario_nuevo,
            host=host,
        )

        try:
            nombre_completo = " ".join(filter(None, [nombre, paterno, materno]))
            _enviar_correo_bienvenida(
                email=email,
                nombre_completo=nombre_completo,
                usuario=usuario_nuevo,
                password_temporal=password_temporal,
            )
        except EmailSendError as email_error:
            raise ValueError(
                "Usuario reactivado pero no se pudo enviar el correo. Contacte al administrador."
            ) from email_error

        return {"Id_Usuario": int(usuario_existente.Id_Usuario)}

    _cargar_temp_usuarios(
        db,
        usuario_objetivo=usuario_nuevo,
        sigla_unidad=unidad.Sigla,
        nombre_rol=rol.Rol,
        email=email,
        nombre=nombre,
        paterno=paterno,
        materno=materno,
        nombre_nivel=nivel.Nivel if nivel else "",
        nombres_formatos=[f.Formato for f in formatos],
    )

    try:
        db.execute(
            text(
                """
                EXEC dbo.SP_Crea_Usuario
                    @PPeriodo = :periodo,
                    @UUnidad_Academica = :unidad,
                    @HHost = :host,
                    @UUsuario = :usuario_operador,
                    @UUsuarioNvo = :usuario_nuevo,
                    @CContrasena = :password,
                    @EEmail = :email,
                    @NNombre = :nombre,
                    @PPaterno = :paterno,
                    @MMaterno = :materno
                """
            ),
            {
                "periodo": periodo_literal,
                "unidad": unidad.Sigla,
                "host": host,
                "usuario_operador": usuario_operador,
                "usuario_nuevo": usuario_nuevo,
                "password": password_hash,
                "email": email,
                "nombre": nombre,
                "paterno": paterno,
                "materno": materno,
            },
        )
        db.commit()

        usuario_creado = (
            db.query(Usuario)
            .filter(Usuario.Usuario == usuario_nuevo)
            .order_by(Usuario.Id_Usuario.desc())
            .first()
        )
        if not usuario_creado:
            raise ValueError("No fue posible confirmar el alta del usuario.")

        _registrar_bitacora_password_temporal(
            db,
            id_usuario=int(usuario_creado.Id_Usuario),
            usuario=usuario_nuevo,
            host=host,
        )

        try:
            nombre_completo = " ".join(filter(None, [nombre, paterno, materno]))
            _enviar_correo_bienvenida(
                email=email,
                nombre_completo=nombre_completo,
                usuario=usuario_nuevo,
                password_temporal=password_temporal,
            )
        except EmailSendError as email_error:
            raise ValueError(
                "Usuario registrado pero no se pudo enviar el correo. Contacte al administrador."
            ) from email_error

        return {"Id_Usuario": int(usuario_creado.Id_Usuario)}

    except Exception:
        db.rollback()
        raise
    finally:
        try:
            _limpiar_temp_usuarios(db, usuario_nuevo)
            db.commit()
        except Exception:
            db.rollback()


def modificar_usuario_sp(
    db: Session,
    id_usuario: int,
    payload: dict[str, Any],
    usuario_operador: str,
    host: str,
) -> Usuario:
    usuario_actual = db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()
    if not usuario_actual:
        raise ValueError("Usuario no encontrado.")

    nombre = _capitalizar_nombre(str(payload.get("Nombre") or usuario_actual.Nombre or "").strip())
    paterno = _capitalizar_nombre(str(payload.get("Paterno") or usuario_actual.Paterno or "").strip())
    materno = _capitalizar_nombre(str(payload.get("Materno") or usuario_actual.Materno or "").strip())
    email = str(payload.get("Email") or usuario_actual.Email or "").strip()

    id_unidad = int(payload.get("Id_Unidad_Academica") or usuario_actual.Id_Unidad_Academica or 0)
    id_rol = int(payload.get("Id_Rol") or usuario_actual.Id_Rol or 0)
    id_nivel_payload = payload.get("Id_Nivel") if "Id_Nivel" in payload else usuario_actual.Id_Nivel
    id_nivel = _to_optional_int(id_nivel_payload)
    id_formatos = [int(x) for x in (payload.get("Id_Formatos") or [])]

    if not id_formatos and id_rol not in ROLES_SIN_FORMATO:
        raise ValueError("Debes seleccionar al menos un formato.")

    unidad, rol, nivel, formatos = _resolver_catalogos(db, id_unidad, id_rol, id_nivel, id_formatos)
    periodo_literal = _get_periodo_literal(db)

    usuario_objetivo = str(usuario_actual.Usuario).strip()
    _cargar_temp_usuarios(
        db,
        usuario_objetivo=usuario_objetivo,
        sigla_unidad=unidad.Sigla,
        nombre_rol=rol.Rol,
        email=email,
        nombre=nombre,
        paterno=paterno,
        materno=materno,
        nombre_nivel=nivel.Nivel if nivel else "",
        nombres_formatos=[f.Formato for f in formatos],
    )

    try:
        db.execute(
            text(
                """
                EXEC dbo.SP_Modifica_Usuario
                    @PPeriodo = :periodo,
                    @UUnidad_Academica = :unidad,
                    @NNivel = :nivel,
                    @HHost = :host,
                    @UUsuario = :usuario_operador,
                    @UUsuarioNvo = :usuario_nuevo,
                    @CContrasena = :password,
                    @EEmail = :email,
                    @NNombre = :nombre,
                    @PPaterno = :paterno,
                    @MMaterno = :materno
                """
            ),
            {
                "periodo": periodo_literal,
                "unidad": unidad.Sigla,
                "nivel": nivel.Nivel if nivel else "",
                "host": host,
                "usuario_operador": usuario_operador,
                "usuario_nuevo": usuario_objetivo,
                "password": usuario_actual.Password,
                "email": email,
                "nombre": nombre,
                "paterno": paterno,
                "materno": materno,
            },
        )

        db.commit()

        # Modo estricto SP-only: no actualizar ORM ni formatos en Python.
        # Solo refrescar el estado persistido por el SP.
        db.refresh(usuario_actual)
        return usuario_actual

    except Exception:
        db.rollback()
        raise
    finally:
        try:
            _limpiar_temp_usuarios(db, usuario_objetivo)
            db.commit()
        except Exception:
            db.rollback()


def baja_usuario_sp(
    db: Session,
    id_usuario: int,
    usuario_operador: str,
    host: str,
) -> Usuario:
    usuario_actual = db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()
    if not usuario_actual:
        raise ValueError("Usuario no encontrado.")

    unidad = (
        db.query(CatUnidadAcademica)
        .filter(CatUnidadAcademica.Id_Unidad_Academica == usuario_actual.Id_Unidad_Academica)
        .first()
    )
    if not unidad:
        raise ValueError("No se encontro la unidad academica del usuario.")

    nivel: CatNivel | None = None
    if usuario_actual.Id_Nivel:
        nivel = db.query(CatNivel).filter(CatNivel.Id_Nivel == usuario_actual.Id_Nivel).first()

    if not nivel and int(usuario_actual.Id_Rol or 0) not in ROLES_SIN_NIVEL:
        raise ValueError("No se encontro el nivel del usuario.")

    nivel_literal = nivel.Nivel if nivel else ""

    rol = db.query(CatRoles).filter(CatRoles.Id_Rol == usuario_actual.Id_Rol).first()
    rol_nombre = rol.Rol if rol else ""

    formato_default = (
        db.query(CatFormatos)
        .filter(CatFormatos.Id_Estatus == 1)
        .order_by(CatFormatos.Id_Formato.asc())
        .first()
    )
    formato_nombre = formato_default.Formato if formato_default else ""

    usuario_objetivo = str(usuario_actual.Usuario or "").strip()
    periodo_literal = _get_periodo_literal(db)

    _cargar_temp_usuarios(
        db,
        usuario_objetivo=usuario_objetivo,
        sigla_unidad=unidad.Sigla,
        nombre_rol=rol_nombre,
        email=str(usuario_actual.Email or ""),
        nombre=str(usuario_actual.Nombre or ""),
        paterno=str(usuario_actual.Paterno or ""),
        materno=str(usuario_actual.Materno or ""),
        nombre_nivel=nivel_literal,
        nombres_formatos=[formato_nombre or "SIN_FORMATO"],
    )

    try:
        db.execute(
            text(
                """
                EXEC dbo.SP_Baja_Usuario
                    @PPeriodo = :periodo,
                    @UUnidad_Academica = :unidad,
                    @UUsuario = :usuario_operador,
                    @NNivel = :nivel,
                    @HHost = :host
                """
            ),
            {
                "periodo": periodo_literal,
                "unidad": unidad.Sigla,
                "usuario_operador": usuario_operador,
                "nivel": nivel_literal,
                "host": host,
            },
        )

        db.commit()
        db.refresh(usuario_actual)

        # Garantiza que la baja logica quede aplicada aunque el SP no confirme cambios.
        if int(usuario_actual.Id_Estatus or 0) != 2:
            usuario_actual.Id_Estatus = 2
            usuario_actual.Fecha_Modificacion = datetime.now(timezone.utc)
            db.commit()
            db.refresh(usuario_actual)

        return usuario_actual

    except Exception:
        db.rollback()
        raise
    finally:
        try:
            _limpiar_temp_usuarios(db, usuario_objetivo)
            db.commit()
        except Exception:
            db.rollback()
