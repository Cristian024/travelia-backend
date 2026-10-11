from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.core.database import close_db, connect_db, get_database
from app.core.exceptions import register_exception_handlers
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.packing_repository import PackingListRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.user_repository import UserRepository

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    db = get_database()
    await UserRepository(db).create_indexes()
    await PlanningRepository(db).create_indexes()
    await ItineraryRepository(db).create_indexes()
    await ExpenseRepository(db).create_indexes()
    await PackingListRepository(db).create_indexes()
    await PaymentRepository(db).create_indexes()
    await PlanRepository(db).create_indexes()
    yield
    await close_db()


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
