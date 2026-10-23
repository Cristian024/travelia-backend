from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    CurrentAdmin,
    get_payment_service,
    get_plan_service,
    get_user_service,
)
from app.schemas.order import OrderResponse, PaginatedOrdersResponse
from app.schemas.payment import PaginatedPaymentsResponse, PaymentResponse
from app.schemas.plan import CreatePlanRequest, PlanResponse, UpdatePlanRequest
from app.schemas.user import (
    PaginatedUsersResponse,
    UpdateUserRoleRequest,
    UserAdminResponse,
)
from app.services.payment_service import PaymentService
from app.services.plan_service import PlanService
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Planes (precios / configuración)
# ---------------------------------------------------------------------------
@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(
    admin: CurrentAdmin,
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> list[PlanResponse]:
    return await service.list_plans()


@router.post("/plans", response_model=PlanResponse, status_code=201)
async def create_plan(
    body: CreatePlanRequest,
    admin: CurrentAdmin,
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanResponse:
    return await service.create_plan(body)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    body: UpdatePlanRequest,
    admin: CurrentAdmin,
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> PlanResponse:
    return await service.update_plan(plan_id, body)


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    admin: CurrentAdmin,
    service: Annotated[PlanService, Depends(get_plan_service)],
) -> None:
    await service.delete_plan(plan_id)


# ---------------------------------------------------------------------------
# Órdenes
# ---------------------------------------------------------------------------
@router.get("/orders", response_model=PaginatedOrdersResponse)
async def list_orders(
    admin: CurrentAdmin,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedOrdersResponse:
    return await service.list_orders(page=page, page_size=page_size)


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    admin: CurrentAdmin,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> OrderResponse:
    return await service.get_order_admin(order_id)


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------
@router.get("/payments", response_model=PaginatedPaymentsResponse)
async def list_payments(
    admin: CurrentAdmin,
    service: Annotated[PaymentService, Depends(get_payment_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedPaymentsResponse:
    return await service.list_payments(page=page, page_size=page_size)


@router.get("/payments/{reference}", response_model=PaymentResponse)
async def get_payment(
    reference: str,
    admin: CurrentAdmin,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    return await service.get_payment_admin(reference)


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    admin: CurrentAdmin,
    service: Annotated[UserService, Depends(get_user_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedUsersResponse:
    return await service.list_users(page=page, page_size=page_size)


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
async def update_user_role(
    user_id: str,
    body: UpdateUserRoleRequest,
    admin: CurrentAdmin,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserAdminResponse:
    return await service.update_role(user_id, body.role)
