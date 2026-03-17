# backend/core/session_store.py
# Simple in-memory session store (no DB, no Redis).
# NOTE: Works best for single-instance deployments. If you run multiple instances, use Redis.

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SessionData:
    id_usuario: int
    usuario: str
    id_rol: int
    nombre_rol: str
    id_nivel: int
    nombre_nivel: str
    id_unidad_academica: int
    sigla_unidad_academica: str
    nombre_usuario: str
    apellidoP_usuario: str
    apellidoM_usuario: str
    requiere_cambio_password: bool = False

    @property
    def nombre_completo(self) -> str:
        parts = [self.nombre_usuario, self.apellidoP_usuario, self.apellidoM_usuario]
        return " ".join([p for p in parts if p])


class InMemorySessionStore:
    def __init__(self) -> None:
        self._lock = RLock()
        # session_id -> (SessionData, expires_at_epoch)
        self._store: Dict[str, tuple[SessionData, float]] = {}

    def create(self, data: SessionData, ttl_seconds: int) -> str:
        session_id = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds
        with self._lock:
            self._store[session_id] = (data, expires_at)
        return session_id

    def get(self, session_id: str) -> Optional[SessionData]:
        if not session_id:
            return None
        with self._lock:
            item = self._store.get(session_id)
            if not item:
                return None
            data, exp = item
            if time.time() >= exp:
                # expired
                self._store.pop(session_id, None)
                return None
            return data

    def delete(self, session_id: str) -> None:
        if not session_id:
            return
        with self._lock:
            self._store.pop(session_id, None)

    def touch(self, session_id: str, ttl_seconds: int) -> None:
        """Extend session expiry (sliding TTL)."""
        if not session_id:
            return
        with self._lock:
            item = self._store.get(session_id)
            if not item:
                return
            data, _ = item
            self._store[session_id] = (data, time.time() + ttl_seconds)


# Global store instance (simple setup)
session_store = InMemorySessionStore()
