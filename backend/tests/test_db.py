from ..database.db_config import SessionLocal
from sqlalchemy import text


def test_conexion():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        print("✅ Conexión exitosa")
    except Exception as e:
        print("❌ Error:", e)
    finally:
        db.close()

test_conexion()