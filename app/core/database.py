import logging

import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_pool: asyncpg.Pool | None = None


def _resolve_dsn() -> tuple[str, str]:
    env = (settings.database_env or "dev").lower()
    dsn = settings.database_prod_url if env == "prod" else settings.database_dev_url
    return env, dsn


async def connect_db() -> None:
    global _pool
    env, dsn = _resolve_dsn()
    if not dsn:
        logger.error("No hay cadena de conexión configurada para el entorno '%s'", env)
        raise RuntimeError(f"Falta la URL de base de datos para el entorno '{env}'")

    # NUNCA se loguea el DSN (contiene credenciales).
    logger.info(
        "Conectando a PostgreSQL (entorno=%s, pool min=%s max=%s)...",
        env, settings.db_min_size, settings.db_max_size,
    )
    try:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=settings.db_min_size,
            max_size=settings.db_max_size,
        )
    except Exception:
        logger.exception("Fallo al conectar a PostgreSQL (entorno=%s)", env)
        raise
    logger.info("Conexión a PostgreSQL establecida.")


async def close_db() -> None:
    global _pool
    if _pool:
        logger.info("Cerrando pool de PostgreSQL...")
        try:
            await _pool.close()
        finally:
            _pool = None
        logger.info("Pool de PostgreSQL cerrado.")


def get_database() -> asyncpg.Pool:
    if _pool is None:
        logger.error("Se intentó usar la base de datos sin inicializar el pool")
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _pool
