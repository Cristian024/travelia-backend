from fastapi import APIRouter
from app.api.v1 import (
    auth,
    users,
    planning,
    itineraries,
    expenses,
    subscriptions,
    payments,
    webhooks,
    admin,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(subscriptions.router)
api_router.include_router(planning.router)
api_router.include_router(itineraries.router)
api_router.include_router(expenses.router)
api_router.include_router(payments.router)
api_router.include_router(admin.router)
api_router.include_router(webhooks.router)
