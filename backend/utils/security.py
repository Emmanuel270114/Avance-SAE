import bcrypt
import secrets
import string

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_random_password(length: int = 12, use_symbols: bool = True) -> str:
    """Genera una contraseña aleatoria segura.

    length: longitud deseada (mínimo 8 recomendado)
    use_symbols: si se incluyen símbolos de puntuación
    """
    if length < 8:
        length = 8
    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        # Filtrar símbolos conflictivos si se desea simplificar: Omitimos comillas y backslash
        symbols = ''.join(ch for ch in string.punctuation if ch not in {'"', "'", '\\'})
        alphabet += symbols
    # Garantizar al menos un dígito y una letra
    pwd = [secrets.choice(string.ascii_lowercase), secrets.choice(string.ascii_uppercase), secrets.choice(string.digits)]
    remaining = length - len(pwd)
    pwd += [secrets.choice(alphabet) for _ in range(remaining)]
    # Mezclar
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)
