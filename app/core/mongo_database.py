import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _resolve_url() -> tuple[str, str]:
    env = (settings.database_env or "dev").lower()
    url = settings.mongodb_prod_url if env == "prod" else settings.mongodb_dev_url
    return env, url


async def connect_mongo() -> None:
    global _client, _db
    env, url = _resolve_url()
    if not url:
        logger.error("No hay URL de MongoDB configurada para el entorno '%s'", env)
        raise RuntimeError(f"Falta la URL de MongoDB para el entorno '{env}'")

    # NUNCA se loguea la URL (contiene credenciales).
    logger.info(
        "Conectando a MongoDB (entorno=%s, db=%s)...", env, settings.mongodb_db_name
    )
    try:
        _client = AsyncIOMotorClient(
            url,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        )
        await _client.admin.command("ping")
        _db = _client[settings.mongodb_db_name]
    except Exception:
        logger.exception("Fallo al conectar a MongoDB (entorno=%s)", env)
        _client = None
        _db = None
        raise
    logger.info("Conexión a MongoDB establecida.")


async def close_mongo() -> None:
    global _client, _db
    if _client:
        logger.info("Cerrando cliente de MongoDB...")
        _client.close()
        _client = None
        _db = None
        logger.info("Cliente de MongoDB cerrado.")


def get_mongo_db() -> AsyncIOMotorDatabase:
    if _db is None:
        logger.error("Se intentó usar MongoDB sin inicializar el cliente")
        raise RuntimeError("MongoDB not initialized. Call connect_mongo() first.")
    return _db
