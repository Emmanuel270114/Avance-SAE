from backend.crud.Usuario import create_usuario
from backend.database.connection import get_db
from backend.schemas.Usuario import UsuarioCreate

nuevo_usuario = UsuarioCreate(
    Id_Unidad_Academica=1,
    Id_Rol=1,
    Usuario="ortega",
    Contraseña="a",
    Email="lortegar1401@alumno.ipn.mx",
    Id_Estatus=1,
)

db = next(get_db())

try:
    unit = create_usuario(db, nuevo_usuario)
    print("Usuario creado con ID:", unit.Id_Usuario)
except Exception as e:
    print("❌ Error en test:", e)
finally:
    db.close()
