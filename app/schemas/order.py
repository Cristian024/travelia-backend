from datetime import datetime

from pydantic import BaseModel

from app.models.order import Order, OrderStatus


class OrderResponse(BaseModel):
    id: str
    user_id: str
    plan_code: str
    amount_in_cents: int
    currency: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            user_id=order.user_id,
            plan_code=order.plan_code,
            amount_in_cents=order.amount_in_cents,
            currency=order.currency,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )


class PaginatedOrdersResponse(BaseModel):
    items: list[OrderResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
