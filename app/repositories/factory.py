"""Factory de repositorios: elige el adaptador según el backend activo.

Es el punto único donde se decide Mongo vs. PostgreSQL, de modo que los
servicios siguen dependiendo solo de los puertos.
"""
from app.core.backend import Backend, get_active_backend
from app.core.database import get_database
from app.core.mongo_database import get_mongo_db
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.mongo.expense_repository import MongoExpenseRepository
from app.repositories.mongo.itinerary_repository import MongoItineraryRepository
from app.repositories.mongo.order_repository import MongoOrderRepository
from app.repositories.mongo.packing_repository import MongoPackingListRepository
from app.repositories.mongo.payment_repository import MongoPaymentRepository
from app.repositories.mongo.plan_repository import MongoPlanRepository
from app.repositories.mongo.planning_repository import MongoPlanningRepository
from app.repositories.mongo.user_repository import MongoUserRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.packing_repository import PackingListRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.user_repository import UserRepository


def _is_mongo() -> bool:
    return get_active_backend() == Backend.mongo


def user_repo():
    return MongoUserRepository(get_mongo_db()) if _is_mongo() else UserRepository(get_database())


def planning_repo():
    return MongoPlanningRepository(get_mongo_db()) if _is_mongo() else PlanningRepository(get_database())


def itinerary_repo():
    return MongoItineraryRepository(get_mongo_db()) if _is_mongo() else ItineraryRepository(get_database())


def expense_repo():
    return MongoExpenseRepository(get_mongo_db()) if _is_mongo() else ExpenseRepository(get_database())


def packing_repo():
    return MongoPackingListRepository(get_mongo_db()) if _is_mongo() else PackingListRepository(get_database())


def order_repo():
    return MongoOrderRepository(get_mongo_db()) if _is_mongo() else OrderRepository(get_database())


def payment_repo():
    return MongoPaymentRepository(get_mongo_db()) if _is_mongo() else PaymentRepository(get_database())


def plan_repo():
    return MongoPlanRepository(get_mongo_db()) if _is_mongo() else PlanRepository(get_database())


async def ensure_schema() -> None:
    """Crea índices/tablas y semillas del backend activo."""
    # `plans` primero: en PostgreSQL `users.subscription_type` tiene FK a plans(code).
    for factory in (
        plan_repo,
        user_repo,
        planning_repo,
        itinerary_repo,
        expense_repo,
        packing_repo,
        order_repo,
        payment_repo,
    ):
        await factory().create_indexes()
