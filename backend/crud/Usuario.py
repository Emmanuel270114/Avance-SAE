#Este archivo contiene las funciones CRUD para el modelo Usuario.

from backend.crud import CatUnidadAcademica
from backend.database.models.Usuario import Usuario
from backend.database.models.CatUnidadAcademica import CatUnidadAcademica
from backend.schemas.Usuario import UsuarioCreate, UsuarioResponse

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from typing import Optional, Sequence

############################__________________FUNCIONES CREATE____________________________############################
def create_usuario(db: Session, user_data: UsuarioCreate) -> Usuario:
    new_user = Usuario(**user_data.model_dump())
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()
        print("❌ Error exacto:", e.orig)
        raise
    return new_user

############################__________________FUNCIONES READ____________________________############################
def read_user_by_username(db: Session, username: str) -> Optional[Usuario]:
    stmt = select(Usuario).where(Usuario.Usuario == username, Usuario.Id_Estatus != 3)
    return db.execute(stmt).scalars().first()

def read_user_by_email(db: Session, email: str) -> Optional[Usuario]:
    stmt = select(Usuario).where(Usuario.Email == email, Usuario.Id_Estatus != 3)
    return db.execute(stmt).scalars().first()

def read_password_by_user(db: Session, username: str) -> Optional[str]:
    stmt = select(Usuario.Contrasena).where(Usuario.Usuario == username)
    result = db.execute(stmt).scalar_one_or_none()
    return result

def read_password_by_email(db: Session, email: str) -> Optional[str]:
    stmt = select(Usuario.Contrasena).where(Usuario.Email == email)
    result = db.execute(stmt).scalar_one_or_none()
    return result

############################__________________FUNCIONES UPDATE____________________________############################

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

def update_usuario(
    db: Session,
    id_usuario: int,
    Nombre: Optional[str],
    Paterno: Optional[str],
    Materno: Optional[str],
    Email: Optional[str],
    Id_Rol: Optional[int],
    UsuarioStr: Optional[str] = None,
    Id_Unidad_Academica: Optional[int] = None,
    Id_Nivel: Optional[int] = None,
):
    from datetime import datetime, timezone
    usuario = db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()
    if not usuario:
        return None
    
    # NORMALIZAR NOMBRES: Capitalizar primera letra de cada palabra
    if Nombre is not None:
        usuario.Nombre = capitalizar_nombre(Nombre)
    if Paterno is not None:
        usuario.Paterno = capitalizar_nombre(Paterno)
    if Materno is not None:
        usuario.Materno = capitalizar_nombre(Materno)
    
    if Email is not None:
        usuario.Email = Email
    if Id_Rol is not None:
        usuario.Id_Rol = Id_Rol
    if UsuarioStr is not None:
        usuario.Usuario = UsuarioStr
    if Id_Unidad_Academica is not None:
        usuario.Id_Unidad_Academica = Id_Unidad_Academica
    if Id_Nivel is not None:
        usuario.Id_Nivel = Id_Nivel
    usuario.Fecha_Modificacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario)
    return usuario

def set_usuario_estatus(db: Session, id_usuario: int, id_estatus: int):
    from datetime import datetime, timezone
    usuario = db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()
    if not usuario:
        return None
    usuario.Id_Estatus = id_estatus
    usuario.Fecha_Modificacion = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario)
    return usuario

############################__________________FUNCIONES LIST/GET____________________________############################
def get_usuarios_by_unidad(db: Session, id_unidad_academica: int) -> Sequence[Usuario]:
    return (
        db.query(Usuario)
        .filter(Usuario.Id_Unidad_Academica == id_unidad_academica, Usuario.Id_Estatus != 3)
        .all()
    )

def get_usuario_by_id(db: Session, id_usuario: int) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.Id_Usuario == id_usuario).first()