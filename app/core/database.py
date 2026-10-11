import asyncpg

from app.config import get_settings

settings = get_settings()

_pool: asyncpg.Pool | None = None


async def connect_db() -> None:
    global _pool
    dbEnv = settings.database_env.lower()
    databaseUrl = ""
    if dbEnv == "prod":
        databaseUrl = settings.database_prod_url
    else:
        databaseUrl = settings.database_dev_url
    _pool = await asyncpg.create_pool(
        dsn=databaseUrl,
        min_size=settings.db_min_size,
        max_size=settings.db_max_size,
    )


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_database() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _pool
