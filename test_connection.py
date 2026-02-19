"""
Script rápido para probar la conexión a la base de datos
"""
import os
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_DRIVER = os.getenv('DB_DRIVER')

print("=" * 60)
print("PRUEBA DE CONEXIÓN A SQL SERVER")
print("=" * 60)
print(f"Host: {DB_HOST}")
print(f"Puerto: {DB_PORT}")
print(f"Base de datos: {DB_NAME}")
print(f"Usuario: {DB_USER}")
print(f"Driver: {DB_DRIVER}")
print("=" * 60)

# Intentar conexión directa con pyodbc
try:
    connection_string = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"Connection Timeout=60;"
        f"Login Timeout=60;"
        f"TrustServerCertificate=yes;"
    )
    
    print("\n[1/3] Intentando conectar con pyodbc...")
    conn = pyodbc.connect(connection_string)
    print("✅ Conexión exitosa con pyodbc!")
    
    print("\n[2/3] Probando consulta simple...")
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()
    print(f"✅ SQL Server Version: {version[0][:50]}...")
    
    print("\n[3/3] Verificando base de datos...")
    cursor.execute("SELECT DB_NAME()")
    db_name = cursor.fetchone()
    print(f"✅ Base de datos actual: {db_name[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
    print("=" * 60)
    
except pyodbc.Error as e:
    print("\n❌ ERROR DE CONEXIÓN:")
    print(f"   {e}")
    print("\n" + "=" * 60)
    print("POSIBLES SOLUCIONES:")
    print("=" * 60)
    print("1. Verificar que SQL Server esté corriendo")
    print("2. Verificar que el host y puerto sean correctos")
    print("3. Verificar credenciales (usuario/contraseña)")
    print("4. Verificar configuración de firewall")
    print("5. Verificar que SQL Server permita conexiones remotas")
    print("6. Verificar que TCP/IP esté habilitado en SQL Server")
    print("=" * 60)
except Exception as e:
    print(f"\n❌ ERROR INESPERADO: {e}")
