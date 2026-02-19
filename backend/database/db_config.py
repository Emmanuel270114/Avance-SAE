
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv
import urllib.parse

# Cargar variables de entorno desde el archivo .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_DRIVER = os.getenv('DB_DRIVER')

# Construir connection string con parámetros adicionales para mejor conectividad
params = urllib.parse.quote_plus(
    f"DRIVER={{{DB_DRIVER}}};"
    f"SERVER={DB_HOST},{DB_PORT};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"Connection Timeout=60;"
    f"Login Timeout=60;"
    f"TrustServerCertificate=yes;"
)

DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

# Configurar engine con pool y timeouts optimizados
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_size=10,  # Tamaño del pool de conexiones
    max_overflow=20,  # Conexiones adicionales permitidas
    pool_recycle=3600,  # Reciclar conexiones cada hora
    connect_args={
        "timeout": 60,
        "connect_timeout": 60
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1"))
        print("La conexión fue exitosa", result.scalar())
    except Exception as e:
        print(f"error en main de db_config: {e}")