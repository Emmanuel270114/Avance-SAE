import backend.database.models
from backend.services.usuario_service import user_already_exists
from backend.database.connection import get_db

db = next(get_db())
ver = user_already_exists(db,"ortega","lortegar1401@alumno.ipn.mx")

if ver:
    print("ya existe")
else:
    print("no existe")