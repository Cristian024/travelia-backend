from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.payment import Payment, PaymentStatus


class CheckoutResponse(BaseModel):
    """Datos que el frontend usa para renderizar el Widget de Wompi.

    `signature_integrity` se corresponde con el campo `signature:integrity`
    que espera el Widget (calculado en el backend con el secreto de integridad).
    """

    payment_id: str
    reference: str
    amount_in_cents: int
    currency: str
    public_key: str
    signature_integrity: str
    redirect_url: str


class CreateTransactionRequest(BaseModel):
    """Datos para crear una transacción server-side (API de Wompi).

    `payment_method` sigue el formato de Wompi, p. ej.:
        {"type": "CARD", "token": "tok_...", "installments": 1}
        {"type": "NEQUI", "phone_number": "3991111111"}
    """

    payment_method: dict[str, Any]
    customer_email: Optional[EmailStr] = None

    @field_validator("payment_method")
    @classmethod
    def _require_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value.get("type"):
            raise ValueError("payment_method.type es obligatorio")
        return value


class TransactionResponse(BaseModel):
    payment_id: str
    reference: str
    transaction_id: Optional[str] = None
    status: PaymentStatus
    amount_in_cents: int
    currency: str


class PaymentResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    user_id: str
    reference: str
    amount_in_cents: int
    currency: str
    status: PaymentStatus
    transaction_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment) -> "PaymentResponse":
        return cls(
            id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            reference=payment.reference,
            amount_in_cents=payment.amount_in_cents,
            currency=payment.currency,
            status=payment.status,
            transaction_id=payment.transaction_id,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )


class PaginatedPaymentsResponse(BaseModel):
    items: list[PaymentResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
