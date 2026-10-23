from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    pending = "PENDING"
    paid = "PAID"
    cancelled = "CANCELLED"
    refunded = "REFUNDED"


class Order(BaseModel):
    """Intención de compra. Un pedido puede tener varios intentos de pago."""

    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    plan_code: str
    amount_in_cents: int
    currency: str = "COP"
    status: OrderStatus = OrderStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
