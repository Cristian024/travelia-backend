from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, get_payment_service
from app.schemas.payment import (
    CheckoutResponse,
    CreateTransactionRequest,
    PaymentResponse,
    TransactionResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
async def create_checkout(
    user_id: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> CheckoutResponse:
    """
    Crea un intento de pago PREMIUM y devuelve los datos para el Widget de Wompi
    (reference, monto, public key y firma de integridad). La firma se calcula en
    el backend; el secreto de integridad nunca se expone.
    """
    return await service.create_checkout(user_id)


@router.post("/transactions", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    body: CreateTransactionRequest,
    user_id: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> TransactionResponse:
    """
    Crea la transacción server-side contra la API de Wompi (llave privada).
    El precio se toma del plan PREMIUM almacenado en base de datos.
    """
    return await service.create_transaction(user_id, body)


@router.get("/{reference}", response_model=PaymentResponse)
async def get_payment(
    reference: str,
    user_id: CurrentUser,
    service: Annotated[PaymentService, Depends(get_payment_service)],
) -> PaymentResponse:
    """Estado del intento de pago (PENDING/APPROVED/DECLINED) por referencia."""
    return await service.get_payment(user_id, reference)
