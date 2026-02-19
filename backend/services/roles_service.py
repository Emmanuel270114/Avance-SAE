from backend.database.models.CatRoles import CatRoles
from backend.crud.CatRoles import create_rol, read_role_by_name, read_all_names_roles, read_id_by_name, read_all_roles
from sqlalchemy.orm import Session
import unicodedata
import re
from backend.schemas.Roles import RolesCreate, RolesResponse

from sqlalchemy.orm import Session

def role_already_exists(db: Session, role_name: str) -> bool:
    role = read_role_by_name(db,role_name)
    validation = role is not None
    return  validation

def register_role(db: Session,role_dict: RolesCreate) -> CatRoles:
    try:
        if role_already_exists(db=db, role_name=role_dict.Rol):
            raise ValueError("role already exist")
        role = create_rol(db, role_dict)
        return role
    finally:
        db.close()

def get_all_roles(db: Session) -> list[RolesResponse]:
    roles = read_all_roles(db)
    return [RolesResponse.model_validate(r) for r in roles]

# --- Nueva lógica de grupos de roles ---

def _normalize(text: str) -> str:
    """Normaliza texto para comparaciones: minúsculas, sin acentos u otros simbolos."""
    t = text.lower().strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")  # remove accents
    t = t.replace("/", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t)
    return t

def _detect_group(role_name: str) -> str | None:
    """Devuelve 'CIIDII', 'UAS' o None según el nombre del rol.
    - CIIDII: Director/a de DII, Jefe/a de Departamento, Jefe de División, Analista
    - UAS: Todos los demás roles, EXCEPTO 'Administrador' y 'Operador'
    - None: Para 'Administrador' y 'Operador' (fuera de grupos)
    """
    n = _normalize(role_name)
    # Excluir explícitos
    if "administrador" in n or "operador" in n:
        return None
    # Palabras clave para CIIDII (tolerando variaciones)
    ciidii_keywords = [
        "director a de dii", "director de dii", "directora de dii", "dii",
        "jefe de division", "jefa de division", "jefe a de division",
        "jefe de departamento", "jefa de departamento", "jefe a de departamento",
        "analista",
    ]
    if any(k in n for k in ciidii_keywords):
        return "CIIDII"
    # Por defecto (excluyendo admin/operador): UAS
    return "UAS"

def get_roles_for_user_group(db: Session, current_role_id: int) -> list[RolesResponse]:
    """Retorna los roles que puede asignar el usuario actual según su rol.
    - Si el rol actual es 'Administrador' u 'Operador' => retorna TODOS los roles.
    - Si pertenece a roles 7, 8, 9 (superiores CIIDII) => puede asignar roles 3, 4, 5, 6, 7, 8, 9
    - Si pertenece a 'CIIDII' (otros) => solo roles 'CIIDII'.
    - Si pertenece a 'UAS' => solo roles 'UAS'.
    """
    roles = read_all_roles(db)
    # Buscar el rol actual
    current_role = next((r for r in roles if r.Id_Rol == current_role_id), None)
    if not current_role:
        # Si no se encuentra, regresar todos por seguridad
        return [RolesResponse.model_validate(r) for r in roles]
    
    # CASO ESPECIAL: Roles superiores 7, 8, 9 pueden asignar roles 3, 4, 5, 6, 7, 8, 9
    if current_role_id in [7, 8, 9]:
        # Roles que pueden asignar: 3, 4, 5 (UAs) + 6 (Analista) + 7, 8, 9 (superiores CIIDII)
        roles_permitidos = [3, 4, 5, 6, 7, 8, 9]
        filtered = [r for r in roles if r.Id_Rol in roles_permitidos]
        return [RolesResponse.model_validate(r) for r in filtered]
    
    current_group = _detect_group(current_role.Rol)
    # Admin/Operador => sin restricción
    if current_group is None:
        return [RolesResponse.model_validate(r) for r in roles]
    # Filtrar por grupo
    filtered = [r for r in roles if _detect_group(r.Rol) == current_group]
    return [RolesResponse.model_validate(r) for r in filtered]
