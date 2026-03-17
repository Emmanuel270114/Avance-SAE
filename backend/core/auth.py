# backend/core/auth.py
from __future__ import annotations

import os
from typing import Iterable, Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.responses import Response

from backend.core.session_store import SessionData, session_store

# Default: 8 hours
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 8)))

def is_secure_cookie() -> bool:
    """Secure cookies require HTTPS. In local dev you may run HTTP."""
    v = os.getenv("COOKIE_SECURE", "").strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off"}:
        return False
    # Auto: secure in common hosted envs
    return os.getenv("ENV", "").lower() in {"prod", "production"} or os.getenv("HTTPS", "").lower() in {"on", "1", "true"}

def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=is_secure_cookie(),
        samesite=os.getenv("COOKIE_SAMESITE", "lax"),
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )

def clear_session_cookie(response: Response) -> None:
    response.delete_cookie("session_id", path="/")

async def get_current_session(
    request: Request,
    session_id: Optional[str] = Cookie(default=None),
) -> SessionData:
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    sess = session_store.get(session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    # Sliding TTL (optional). Comment out if you prefer fixed expiry.
    session_store.touch(session_id, SESSION_TTL_SECONDS)
    request.state.session = sess
    request.state.session_id = session_id
    return sess

def require_roles(*allowed_roles: int):
    allowed = set(allowed_roles)
    async def _dep(sess: SessionData = Depends(get_current_session)) -> SessionData:
        if sess.id_rol not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return sess
    return _dep
