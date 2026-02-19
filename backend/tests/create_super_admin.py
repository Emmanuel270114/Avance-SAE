"""
Script para crear el usuario super admin del sistema
"""
import sys
import os

# Agregar el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, root_dir)

from backend.database.connection import get_db
from backend.services.usuario_service import register_usuario
from backend.schemas.Usuario import UsuarioCreate

def create_super_admin():
    """Crear el usuario super admin del sistema"""
    db = next(get_db())
    
    try:
        # Datos del super admin
        super_admin_data = UsuarioCreate(
            Nombre="admin",
            Paterno="admin", 
            Materno="admin",
            Email="admin@sistema.com",
            Usuario="superadmin",
            Password="admin123",  # Contraseña temporal
            Id_Unidad_Academica=1,  # Puede ser cualquier UA
            Id_Rol=1  # Rol de administrador
        )
        
        usuario_creado = register_usuario(db, super_admin_data)
        print(f"✅ Super admin creado exitosamente:")
        print(f"   ID: {usuario_creado.Id_Usuario}")
        print(f"   Nombre: {usuario_creado.Nombre} {usuario_creado.Paterno} {usuario_creado.Materno}")
        print(f"   Usuario: {usuario_creado.Usuario}")
        print(f"   Email: {usuario_creado.Email}")
        print(f"   Contraseña: admin123 (cámbiala después del primer login)")
        
    except Exception as e:
        print(f"❌ Error creando super admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()