from backend.crud.CatRoles import read_all_roles
from backend.database.connection import get_db

db = next(get_db())

try:
    unit = read_all_roles(db)
    print(unit)
except Exception as e:
    print("❌ Error en test:", e)
finally:
    db.close()