from backend.crud.CatUnidadAcademica import read_all_unidades
from backend.database.connection import get_db

db = next(get_db())

try:
    unit = read_all_unidades(db)
    print(unit)
except Exception as e:
    print("❌ Error en test:", e)
finally:
    db.close()