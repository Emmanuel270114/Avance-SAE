import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.connection import get_db
from backend.services.usuario_service import is_super_admin
from backend.crud.Usuario import read_user_by_username
from sqlalchemy.orm import Session

def check_super_admin():
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # Buscar usuarios que podrían ser super admin
        print("Verificando usuarios existentes...")
        
        # Verificar directamente la función is_super_admin
        result = is_super_admin("admin", "admin", "admin")
        print(f"is_super_admin('admin', 'admin', 'admin'): {result}")
        
        # Buscar usuario con username "admin"
        user_admin = read_user_by_username(db, "admin")
        if user_admin:
            print(f"Usuario 'admin' encontrado:")
            print(f"  - ID: {user_admin.Id_Usuario}")
            print(f"  - Nombre: {user_admin.Nombre}")
            print(f"  - Paterno: {user_admin.Paterno}")
            print(f"  - Materno: {user_admin.Materno}")
            print(f"  - Email: {user_admin.Email}")
            print(f"  - UA: {user_admin.Id_Unidad_Academica}")
            print(f"  - Rol: {user_admin.Id_Rol}")
            print(f"  - Estatus: {user_admin.Id_Estatus}")
            
            # Verificar si es super admin
            es_super = is_super_admin(user_admin.Nombre, user_admin.Paterno, user_admin.Materno)
            print(f"  - Es super admin: {es_super}")
        else:
            print("Usuario 'admin' no encontrado")
            
        # Buscar cualquier usuario con nombre "admin admin admin"
        from backend.database.models.Usuario import Usuario
        usuarios_admin = db.query(Usuario).filter(
            Usuario.Nombre == "admin",
            Usuario.Paterno == "admin", 
            Usuario.Materno == "admin"
        ).all()
        
        print(f"\nUsuarios con nombre 'admin admin admin': {len(usuarios_admin)}")
        for user in usuarios_admin:
            print(f"  - Usuario: {user.Usuario}")
            print(f"  - Email: {user.Email}")
            print(f"  - ID: {user.Id_Usuario}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_super_admin()