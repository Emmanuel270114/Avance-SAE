from typing import Optional


def get_request_host(request) -> str:
    """Obtiene el host preferido a partir de la Request (X-Forwarded-For -> reverse DNS) o devuelve la IP.

    - Si no hay request, devuelve "sistema".
    - Si no hay IP disponible, devuelve cadena vacía.
    """
    try:
        if not request:
            return "sistema"
        xff = request.headers.get("x-forwarded-for") or ""
        client_ip = (xff.split(",")[0].strip() if xff else (request.client.host if request.client else ""))
        if not client_ip:
            return ""
        try:
            import socket
            return socket.gethostbyaddr(client_ip)[0]
        except Exception:
            return client_ip
    except Exception:
        return ""
