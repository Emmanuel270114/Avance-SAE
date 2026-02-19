import backend.database.models
from backend.services.usuario_service import register_usuario
from backend.database.connection import get_db
from backend.schemas.usuario import UsuarioCreate

nuevo_usuario = UsuarioCreate(
    Id_Unidad_Academica=1,
    Id_Rol=1,
    Usuario="ortega3",
    Contraseña="a",
    Email="lortegar1403@alumno.ipn.mx",
    Id_Estatus=1,
)

try:
    db = next(get_db())
    user = register_usuario(db,nuevo_usuario)
    print("Usuario creado con ID:", user.Id_Usuario)
except ValueError as e:
    print("Error al registrar usuario:", e)