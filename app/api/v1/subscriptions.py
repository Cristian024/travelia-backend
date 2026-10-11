from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_subscription_service
from app.schemas.plan import PlanResponse
from app.schemas.subscription import ChangeSubscriptionRequest, SubscriptionResponse
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/plans", response_model=list[PlanResponse])
async def list_available_plans(
    user_id: CurrentUser,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> list[PlanResponse]:
    """Lista las suscripciones disponibles (planes activos) para que el usuario elija."""
    return await service.list_available_plans()


@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    user_id: CurrentUser,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Devuelve el plan actual, límites y consumo mensual."""
    return await service.get_status(user_id)


@router.post("/me", response_model=SubscriptionResponse)
async def change_my_subscription(
    body: ChangeSubscriptionRequest,
    user_id: CurrentUser,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Cambia el plan del usuario (FREE <-> PREMIUM).

    Nota: aquí se simula el cambio. En producción debe validarse el pago
    (webhook de la pasarela) antes de otorgar PREMIUM.
    """
    return await service.change_plan(user_id, body.subscription_type)
