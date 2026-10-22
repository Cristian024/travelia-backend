"""Selector de backend de persistencia (circuit breaker).

- `DATABASE_BACKEND=mongo` (por defecto) o `postgres`.
- Si el backend primario no conecta y `DATABASE_FALLBACK_ENABLED=true`,
  se usa el otro backend (respaldo) en tiempo de ejecución.
"""
import logging
from enum import Enum

from app.config import get_settings
from app.core.database import close_db, connect_db
from app.core.mongo_database import close_mongo, connect_mongo

logger = logging.getLogger(__name__)

settings = get_settings()


class Backend(str, Enum):
    mongo = "mongo"
    postgres = "postgres"


_active: Backend | None = None


def configured_backend() -> Backend:
    value = (settings.database_backend or "mongo").strip().lower()
    return Backend.postgres if value == "postgres" else Backend.mongo


def get_active_backend() -> Backend:
    return _active or configured_backend()


def _set_active(backend: Backend) -> None:
    global _active
    _active = backend


async def connect_backend(backend: Backend) -> None:
    if backend == Backend.mongo:
        await connect_mongo()
    else:
        await connect_db()
    _set_active(backend)


async def connect_with_fallback() -> Backend:
    primary = configured_backend()
    try:
        await connect_backend(primary)
        logger.info("Backend de persistencia activo: %s", primary.value)
        return primary
    except Exception:
        logger.exception("No se pudo conectar al backend primario '%s'", primary.value)
        if not settings.database_fallback_enabled:
            raise
        fallback = Backend.postgres if primary == Backend.mongo else Backend.mongo
        logger.warning("Aplicando fallback al backend '%s'", fallback.value)
        await connect_backend(fallback)
        logger.info("Backend de persistencia activo (fallback): %s", fallback.value)
        return fallback


async def close_backend() -> None:
    if get_active_backend() == Backend.mongo:
        await close_mongo()
    else:
        await close_db()
