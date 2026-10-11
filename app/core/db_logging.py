"""Envoltorio de `asyncpg.Pool` para registrar las queries SQL ejecutadas.

Se activa con `LOG_SQL_QUERIES=true`. Por seguridad solo se registra el texto
SQL (no los parámetros, que pueden contener datos sensibles como hashes o emails).
"""
import logging
from typing import Any

logger = logging.getLogger("sql")


def _format(query: Any) -> str:
    return " ".join(str(query).split())


class _LoggedConnection:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    @staticmethod
    def _log_query(query: Any, args: Any) -> None:
        logger.debug("Executing Query:  %s with params %s", _format(query), args)

    async def execute(self, query, *args, **kwargs):
        self._log_query(query, args)
        return await self._conn.execute(query, *args, **kwargs)

    async def fetch(self, query, *args, **kwargs):
        self._log_query(query, args)
        return await self._conn.fetch(query, *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        self._log_query(query, args)
        return await self._conn.fetchrow(query, *args, **kwargs)

    async def fetchval(self, query, *args, **kwargs):
        self._log_query(query, args)
        return await self._conn.fetchval(query, *args, **kwargs)

    def transaction(self, *args, **kwargs):
        return self._conn.transaction(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


class _AcquireContext:
    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self._ctx = None

    async def __aenter__(self) -> _LoggedConnection:
        self._ctx = self._pool.acquire()
        conn = await self._ctx.__aenter__()
        return _LoggedConnection(conn)

    async def __aexit__(self, exc_type, exc, tb):
        return await self._ctx.__aexit__(exc_type, exc, tb)


class LoggedPool:
    """Proxy de `asyncpg.Pool` que loguea cada query en el logger 'sql'."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    def acquire(self) -> _AcquireContext:
        return _AcquireContext(self._pool)

    async def execute(self, query, *args, **kwargs):
        logger.debug("Executing Query:  %s with params %s", _format(query), args)
        return await self._pool.execute(query, *args, **kwargs)

    async def fetch(self, query, *args, **kwargs):
        logger.debug("Executing Query:  %s with params %s", _format(query), args)
        return await self._pool.fetch(query, *args, **kwargs)

    async def fetchrow(self, query, *args, **kwargs):
        logger.debug("Executing Query:  %s with params %s", _format(query), args)
        return await self._pool.fetchrow(query, *args, **kwargs)

    async def fetchval(self, query, *args, **kwargs):
        logger.debug("Executing Query:  %s with params %s", _format(query), args)
        return await self._pool.fetchval(query, *args, **kwargs)

    async def close(self):
        return await self._pool.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._pool, name)
