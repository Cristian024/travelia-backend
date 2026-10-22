import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.logging_factory import build_logging_adapter
from app.api.v1.router import api_router
from app.config import get_settings
from app.core.backend import close_backend, connect_with_fallback
from app.core.exceptions import register_exception_handlers
from app.repositories.factory import ensure_schema

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    build_logging_adapter(settings).configure()
    logger.info(
        "Iniciando %s v%s (log_target=%s, backend=%s)",
        settings.app_name,
        settings.app_version,
        settings.log_target or "local",
        settings.database_backend,
    )
    try:
        await connect_with_fallback()
        await ensure_schema()
        logger.info("Esquema de base de datos verificado/creado.")
    except Exception:
        logger.exception("Fallo al inicializar la persistencia")
        raise
    yield
    logger.info("Apagando aplicación...")
    await close_backend()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "version": settings.app_version}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
