from threading import Lock

# Bandera en memoria para usuarios con contraseña temporal.
# No persiste entre reinicios del servidor.
_lock = Lock()
_temp_password_users: set[int] = set()

def mark_temp(user_id: int) -> None:
    """Marcar a un usuario como que tiene contraseña temporal."""
    with _lock:
        _temp_password_users.add(int(user_id))

def is_temp(user_id: int) -> bool:
    """Verificar si el usuario requiere cambio de contraseña."""
    with _lock:
        return int(user_id) in _temp_password_users

def clear_temp(user_id: int) -> None:
    """Quitar la marca de contraseña temporal para el usuario."""
    with _lock:
        _temp_password_users.discard(int(user_id))
